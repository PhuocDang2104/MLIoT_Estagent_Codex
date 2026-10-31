"""Untrusted model proposals become bounded, explicitly confirmed graph inputs."""
from .models import EditPlan, Review
from .graph import validate_review


def validate_plan(value, state):
    plan = EditPlan.model_validate(value)
    ids = {r['checkpoint_id'] for r in state['rooms']}
    edits = [r.checkpoint_id for r in plan.rooms]
    scripts = [s.checkpoint_id for s in plan.scripts]
    if len(set(edits)) != len(edits) or not set(edits) <= ids:
        raise ValueError('Unknown or duplicate room')
    if len(set(scripts)) != len(scripts) or not set(scripts) <= ids:
        raise ValueError('Unknown or duplicate script')
    sources = {'description', *(r['asset_id'] for r in state['rooms'])}
    if any(not set(s.sources) <= sources for s in plan.scripts):
        raise ValueError('Unknown evidence')
    if plan.order is not None and (len(plan.order) != len(ids) or set(plan.order) != ids):
        raise ValueError('Order must include each checkpoint exactly once')
    if any(v is not None and not v.strip() for r in plan.rooms for v in (r.label, r.summary)):
        raise ValueError('Empty room text')
    if plan.connections is not None:
        validate_review(Review(kind='spatial', decision='approve', request_id='validate-edit',
            rooms=[{k:r[k] for k in ('checkpoint_id','label','yaw')} for r in state['rooms']],
            connections=plan.connections), state['rooms'])
    # Do not create a paid regeneration for an unchanged/model-filled field.
    by_id = {r['checkpoint_id']:r for r in state['rooms']}
    normalized = []
    for edit in plan.rooms:
        for field in ('label','summary','yaw'):
            if getattr(edit,field) == by_id[edit.checkpoint_id].get(field):
                setattr(edit,field,None)
        if any(getattr(edit,field) is not None for field in ('label','summary','yaw')):
            normalized.append(edit)
    plan.rooms = normalized
    old_script = state.get('script') or {}
    old_segments = {s['checkpoint_id']:s for s in old_script.get('segments',[])}
    plan.scripts = [s for s in plan.scripts if s.model_dump() != old_segments.get(s.checkpoint_id)]
    if plan.introduction == old_script.get('introduction'):
        plan.introduction = None
    if plan.order == [r['checkpoint_id'] for r in state['rooms']]:
        plan.order = None
    if plan.connections is not None:
        key = lambda link:(link['source'],link['target'],link['yaw'],link['pitch'])
        if sorted(map(key,[link.model_dump() for link in plan.connections])) == sorted(map(key,state['connections'])):
            plan.connections = None
    route = ('spatial_review' if plan.connections is not None or any(r.yaw is not None for r in plan.rooms)
             else 'semantic' if plan.rooms else 'navigation' if plan.order is not None else 'narration')
    if not state.get('model'):
        # A pre-geometry edit must never jump over the required worker boundary.
        route = 'spatial_review'
    changed = bool(plan.rooms or plan.scripts or plan.introduction is not None or
                   plan.order is not None or plan.connections is not None)
    return plan.model_dump(), route, changed


def apply_plan(state):
    # Apply the normalized allowlisted plan already checked before enqueue.
    plan = state['edit_plan']
    edits = {r['checkpoint_id']: r for r in plan['rooms']}
    rooms = [{**r, **{k:v for k,v in edits.get(r['checkpoint_id'], {}).items()
                      if k != 'checkpoint_id' and v is not None}} for r in state['rooms']]
    if plan['order'] is not None:
        by_id = {r['checkpoint_id']:r for r in rooms}
        rooms = [by_id[key] for key in plan['order']]
    invalid = {}
    if state['edit_route'] == 'spatial_review':
        rooms = [{k:v for k,v in r.items() if k != 'anchor'} for r in rooms]
        invalid = {'model':None, 'navigation_config':[], 'itinerary':[]}
    return {**invalid, 'rooms': rooms, 'connections': plan['connections'] if plan['connections'] is not None else state['connections'],
            'approved': False, 'rejected': False, 'package': None,
            'reuse_script': not bool(plan['rooms']), 'script_overrides': plan,
            'previous_script': state.get('script'), 'previous_audio': state.get('audio', []), 'audio': []}
