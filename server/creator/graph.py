"""Durable business workflow. Each paid operation has its own checkpointed node."""
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from .models import Brief, Observation, Script, Review
from .package import Room, Narration, Geometry

STEPS = {
    'understand': 'Phân tích thông tin bất động sản',
    'scene': 'Nhận diện từng không gian',
    'spatial': 'Chuẩn bị sơ đồ và checkpoint',
    'spatial_review': 'Kiểm tra bố cục không gian',
    'build_model': 'Dựng mô hình nhà 3D',
    'mapping': 'Liên kết phòng và panorama',
    'semantic': 'Tổng hợp thông tin có nguồn',
    'navigation': 'Tạo điều hướng tham quan',
    'narration': 'Soạn lời giới thiệu từng khu',
    'final_review': 'Duyệt nội dung tour',
    'voice': 'Tạo giọng giới thiệu',
    'assemble': 'Kiểm tra gói tour',
}


class State(TypedDict, total=False):
    project: dict
    assets: list[dict]
    brief: dict
    observations: list[dict]
    rooms: list[dict]
    connections: list[dict]
    model: dict
    script: dict
    audio: list[dict]
    approved: bool
    rejected: bool
    package: dict
    navigation_config: list[dict]
    itinerary: list[str]


def validate_review(review, rooms):
    ids = {r['checkpoint_id'] for r in rooms}
    if review.kind == 'spatial' and review.decision == 'approve':
        if {r.checkpoint_id for r in review.rooms} != ids or len(review.rooms) != len(ids):
            raise ValueError('All checkpoints must be reviewed exactly once')
        links = [(x.source, x.target) for x in review.connections]
        if len(set(links)) != len(links) or any(a == b or a not in ids or b not in ids for a, b in links):
            raise ValueError('Invalid checkpoint connection')
        if any((b, a) not in links for a, b in links):
            raise ValueError('Connections must be confirmed in both directions')
        reachable = {next(iter(ids))}
        while True:
            expanded = reachable | {b for a, b in links if a in reachable}
            if expanded == reachable:
                break
            reachable = expanded
        if reachable != ids:
            raise ValueError('Every checkpoint needs a confirmed route')
    if review.kind == 'final' and review.scripts:
        if {s.checkpoint_id for s in review.scripts} != ids or len(review.scripts) != len(ids):
            raise ValueError('One narration segment is required per checkpoint')


def build_graph(provider, saver, emit, read_asset, write_audio, write_model, worker=None):
    def understand(s):
        return {'brief': Brief.model_validate(provider.brief(s['project'])).model_dump()}

    def scene(s):
        # One panorama per superstep: resume never repeats completed image calls.
        done = list(s.get('observations', []))
        asset = [a for a in s['assets'] if a['kind'] == 'panorama'][len(done)]
        observation = Observation.model_validate(provider.observe(s['project'], asset, read_asset(asset)))
        done.append({'asset_id': asset['id'], **observation.model_dump()})
        return {'observations': done}

    def spatial(s):
        assets = {a['id']: a for a in s['assets']}
        return {'rooms': [
            {'checkpoint_id': f'cp{i+1:02}', 'room_id': f'r{i+1:02}',
             'asset_id': o['asset_id'], 'label': o['label'], 'yaw': 0,
             'projection': assets[o['asset_id']].get('projection', 'photo'),
             'summary': o['summary'], 'facts': o['facts'], 'estimated': True}
            for i, o in enumerate(s['observations'])
        ], 'connections': []}

    def spatial_review(s):
        review = Review.model_validate(interrupt({'kind': 'spatial',
            'message': 'Xác nhận tên khu, hướng nhìn và đường nối thực tế. Chưa có số đo hình học.'}))
        validate_review(review, s['rooms'])
        edits = {r.checkpoint_id: r.model_dump() for r in review.rooms}
        return {'rejected': review.decision == 'reject',
                'rooms': [{**r, **edits.get(r['checkpoint_id'], {})} for r in s['rooms']],
                'connections': [c.model_dump() for c in review.connections]}

    def model(s):
        if worker is None:
            interrupt({'kind': 'integration', 'message':
                'Bố cục đã lưu. Cần kết nối worker dựng 3D để tiếp tục.'})
            # Browser review endpoints cannot resume this boundary.
            raise ValueError('Geometry adapter is not configured')
        return {'model': write_model(s['project'], worker.build(
            s['project'], s['rooms'], s['connections'], s['assets']))}

    def mapping(s):
        anchors = s['model'].get('anchors', {})
        if set(anchors) != {r['checkpoint_id'] for r in s['rooms']}:
            raise ValueError('Geometry worker returned incomplete anchors')
        if any(anchors[r['checkpoint_id']].get('room_id') != r['room_id'] for r in s['rooms']):
            raise ValueError('Geometry worker room mapping does not match checkpoints')
        return {'rooms': [{**r, 'anchor': anchors[r['checkpoint_id']]} for r in s['rooms']]}

    def semantic(s):
        # Preserve provenance. LLM cannot promote an inference to a verified fact.
        return {'rooms': [{**r, 'facts': [f for f in r['facts']
                 if f['provenance'] in ('verified', 'observed')]} for r in s['rooms']]}

    def narration(s):
        script = Script.model_validate(provider.script(s['project'], s['rooms'], s['brief']))
        ids = {r['checkpoint_id'] for r in s['rooms']}
        allowed = {'description', *(r['asset_id'] for r in s['rooms'])}
        if (len(script.segments) != len(ids) or {x.checkpoint_id for x in script.segments} != ids
                or any(not set(x.sources) <= allowed for x in script.segments)):
            raise ValueError('Narration does not match checkpoint evidence')
        return {'script': script.model_dump()}

    def navigation(s):
        rooms = {r['checkpoint_id']: r for r in s['rooms']}
        adjacency = {key: [] for key in rooms}
        hotspots = []
        for link in s['connections']:
            adjacency[link['source']].append(link['target'])
            hotspots.append({**link, 'label': rooms[link['target']]['label'],
                             'target_yaw': rooms[link['target']]['yaw']})
        first = s['rooms'][0]['checkpoint_id']
        itinerary, visited = [first], {first}
        def visit(current):
            for target in adjacency[current]:
                if target in visited:
                    continue
                visited.add(target)
                itinerary.append(target)
                visit(target)
                itinerary.append(current)
        visit(first)
        if visited != set(rooms):
            raise ValueError('Tour navigation is not connected')
        return {'navigation_config': hotspots, 'itinerary': itinerary}

    def final_review(s):
        review = Review.model_validate(interrupt({'kind': 'final',
            'message': 'Kiểm tra nội dung và mô hình trước khi tạo giọng đọc.'}))
        validate_review(review, s['rooms'])
        script = dict(s['script'])
        if review.scripts:
            allowed = {'description', *(r['asset_id'] for r in s['rooms'])}
            if any(not set(x.sources) <= allowed for x in review.scripts):
                raise ValueError('Invalid narration evidence')
            script['segments'] = [x.model_dump() for x in review.scripts]
        return {'script': script, 'approved': review.decision == 'approve',
                'rejected': review.decision == 'reject'}

    def voice(s):
        done = list(s.get('audio', []))
        segments = [{'checkpoint_id': 'introduction', 'text': s['script']['introduction']},
                    *s['script']['segments']]
        segment = segments[len(done)]
        done.append(write_audio(s['project'], segment['checkpoint_id'],
                                provider.speech(s['project'], segment['text'])))
        return {'audio': done}

    def assemble(s):
        Geometry.model_validate(s['model'])
        for room in s['rooms']:
            Room.model_validate(room)
        narration = Narration.model_validate({**s['script'], 'audio': s['audio']})
        if {a.checkpoint_id for a in narration.audio} != {'introduction', *(r['checkpoint_id'] for r in s['rooms'])}:
            raise ValueError('Audio does not cover every checkpoint')
        return {'package': {'version': 1, 'id': s['project']['id'],
            'generation_id': s['project']['generation_id'], 'name': s['project']['name'],
            'locale': s['project']['locale'], 'rooms': s['rooms'],
            'connections': s['connections'], 'model': s['model'],
            'navigation': s['navigation_config'], 'itinerary': s['itinerary'],
            'narration': {**s['script'], 'audio': s['audio']},
            'music': next((a for a in s['assets'] if a['kind'] == 'music'), None),
            'approved': s['approved'], 'ai_voice_disclosure': True}}

    builder = StateGraph(State)
    handlers = {'understand': understand, 'scene': scene, 'spatial': spatial,
        'spatial_review': spatial_review, 'build_model': model, 'mapping': mapping,
        'semantic': semantic, 'navigation': navigation, 'narration': narration,
        'final_review': final_review, 'voice': voice, 'assemble': assemble}
    for name, handler in handlers.items():
        def run(state, fn=handler, node=name):
            emit(state['project']['generation_id'], node, 'running', STEPS[node])
            result = fn(state)  # Do not catch GraphInterrupt.
            emit(state['project']['generation_id'], node, 'completed', STEPS[node])
            return result
        builder.add_node(name, run)
    builder.add_edge(START, 'understand')
    builder.add_edge('understand', 'scene')
    builder.add_conditional_edges('scene', lambda s: 'scene' if len(s['observations']) <
        len([a for a in s['assets'] if a['kind'] == 'panorama']) else 'spatial')
    builder.add_edge('spatial', 'spatial_review')
    builder.add_conditional_edges('spatial_review', lambda s: END if s.get('rejected') else 'build_model')
    chain = ['build_model', 'mapping', 'semantic', 'navigation', 'narration', 'final_review']
    for left, right in zip(chain, chain[1:]):
        builder.add_edge(left, right)
    builder.add_conditional_edges('final_review', lambda s: END if s.get('rejected') else 'voice')
    builder.add_conditional_edges('voice', lambda s: 'voice' if len(s['audio']) <
        len(s['script']['segments']) + 1 else 'assemble')
    builder.add_edge('assemble', END)
    return builder.compile(checkpointer=saver)
