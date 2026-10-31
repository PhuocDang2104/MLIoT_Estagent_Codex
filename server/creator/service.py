import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from fastapi import HTTPException
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from .graph import build_graph, validate_review
from .store import Store, uid, now
from .package import PublishedTour
from .models import ViewerAnswer


class Creator:
    """One process/one execution worker. PostgreSQL/queue adapters can replace this seam."""
    def __init__(self, root, provider=None, worker=None, *, object_storage=None, storage_limits=None):
        self.store = Store(root, object_storage=object_storage, storage_limits=storage_limits)
        self.provider = provider
        self.worker = worker
        self.connection = sqlite3.connect(root / 'graph.sqlite', check_same_thread=False)
        try:
            self.graph = build_graph(provider, SqliteSaver(self.connection), self.store.emit,
                self.store.content, self.store.write_audio, self.store.write_model, worker)
        except BaseException:
            self.connection.close()
            self.store.db.close()
            raise
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='creator')
        self.active = set()

    def close(self):
        self.pool.shutdown(wait=True, cancel_futures=True)
        self.connection.close()
        self.store.db.close()

    def config(self, generation_id):
        return {'configurable': {'thread_id': generation_id}, 'recursion_limit': 100}

    def generation(self, owner, generation_id):
        rows = self.store.rows('SELECT * FROM generations WHERE id=?', (generation_id,))
        if not rows:
            raise HTTPException(404, 'Không tìm thấy lần tạo tour.')
        self.store.project(owner, rows[0]['project'])
        row = rows[0]
        snapshot = self.graph.get_state(self.config(generation_id))
        values = snapshot.values
        review = next((i.value for t in snapshot.tasks for i in t.interrupts), None)
        return {'id': generation_id, 'project_id': row['project'], 'status': row['status'],
                'error': row['error'], 'attempts': row['attempts'], 'review': review,
                'brief': values.get('brief'), 'rooms': values.get('rooms', []),
                'connections': values.get('connections', []), 'script': values.get('script'),
                'model': values.get('model'), 'package': values.get('package'),
                'observations': values.get('observations', []),
                'events': self.store.events(generation_id)}

    def project(self, owner, project_id):
        return {**self.store.project(owner, project_id), 'assets': self.store.assets(project_id),
                'generations': self.store.rows('SELECT id,status,error FROM generations WHERE project=? ORDER BY rowid DESC', (project_id,)),
                'published': self.store.rows('SELECT id,generation FROM published WHERE project=? ORDER BY rowid DESC', (project_id,))}

    def create(self, owner, data):
        def operation():
            if len(self.store.rows('SELECT id FROM projects WHERE owner=?', (owner,))) >= 10:
                raise HTTPException(429, 'Phiên này đã đạt giới hạn 10 project.')
            project = {'id': uid(), 'created_at': now(), **data.model_dump(exclude={'request_id'})}
            self.store.execute('INSERT INTO projects VALUES(?,?,?)', (project['id'], owner, json.dumps(project, ensure_ascii=False)))
            return {'id': project['id']}
        return self.store.action(owner, data.request_id, {'create': data.model_dump()}, operation)

    def start(self, owner, project_id, request_id):
        def operation():
            if self.provider is None:
                raise HTTPException(503, 'Cần cấu hình OpenAI ở backend để tạo tour.')
            project = self.store.project(owner, project_id)
            assets = self.store.assets(project_id)
            panoramas = [a for a in assets if a['kind'] == 'panorama']
            if not 1 <= len(panoramas) <= 12:
                raise HTTPException(422, 'Cần từ 1 đến 12 ảnh panorama.')
            runs = self.store.rows('SELECT status FROM generations WHERE project=?', (project_id,))
            if runs:
                raise HTTPException(409, 'Dữ liệu đã khóa trong lần tạo tour. Tạo project mới để thay đầu vào.')
            if len(self.store.rows("SELECT id FROM generations WHERE status IN ('queued','running')")) >= 8:
                raise HTTPException(429, 'Hàng đợi đang đầy. Vui lòng thử sau.')
            generation_id = uid()
            self.store.execute('INSERT INTO generations(id,project,status,attempts) VALUES(?,?,?,1)', (generation_id, project_id, 'queued'))
            return {'id': generation_id}
        result = self.store.action(owner, request_id, {'start': project_id}, operation)
        project = self.store.project(owner, project_id)
        self.enqueue(result['id'], {'project': {**project, 'generation_id': result['id']},
                                    'assets': self.store.assets(project_id)})
        return result

    def resume(self, owner, generation_id, review):
        def operation():
            current = self.generation(owner, generation_id)
            if current['status'] != 'needs_review' or not current['review'] or current['review']['kind'] != review.kind:
                raise HTTPException(409, 'Bước duyệt đã thay đổi. Tải lại dữ liệu.')
            try:
                validate_review(review, current['rooms'])
                if review.kind == 'final' and review.scripts:
                    allowed = {'description', *(r['asset_id'] for r in current['rooms'])}
                    if any(not set(x.sources) <= allowed for x in review.scripts):
                        raise ValueError('Invalid evidence')
            except ValueError as error:
                raise HTTPException(422, str(error)) from None
            self.store.execute("UPDATE generations SET status='queued',error=NULL WHERE id=?", (generation_id,))
            return {'id': generation_id}
        result = self.store.action(owner, review.request_id, {'review': generation_id, **review.model_dump()}, operation)
        self.enqueue(generation_id, Command(resume=review.model_dump()))
        return result

    def retry(self, owner, generation_id, request_id):
        def operation():
            current = self.generation(owner, generation_id)
            if self.provider is None:
                raise HTTPException(503, 'Cần cấu hình OpenAI ở backend.')
            integration_ready = current['status'] == 'waiting_integration' and self.worker is not None
            if not integration_ready and (current['status'] != 'failed' or current['review']):
                raise HTTPException(409, 'Lần tạo tour này không cần chạy lại.')
            if current['attempts'] >= 3:
                raise HTTPException(429, 'Đã hết 3 lần thử. Kiểm tra cấu hình trước khi tạo project mới.')
            self.store.execute("UPDATE generations SET status='queued',error=NULL,attempts=attempts+1 WHERE id=?", (generation_id,))
            return {'id': generation_id}
        result = self.store.action(owner, request_id, {'retry': generation_id}, operation)
        snapshot = self.graph.get_state(self.config(generation_id))
        if any(i.value.get('kind') == 'integration' for t in snapshot.tasks for i in t.interrupts) and self.worker is not None:
            payload = Command(resume=True)
        elif snapshot.values:
            payload = None
        else:
            row = self.store.rows('SELECT project FROM generations WHERE id=?', (generation_id,))[0]
            payload = {'project': {**self.store.project(owner, row['project']), 'generation_id': generation_id},
                       'assets': self.store.assets(row['project'])}
        self.enqueue(generation_id, payload)
        return result

    def enqueue(self, generation_id, payload):
        with self.store.lock:
            status = self.store.rows('SELECT status FROM generations WHERE id=?', (generation_id,))[0]['status']
            if generation_id in self.active or status != 'queued':
                return
            self.active.add(generation_id)
            self.pool.submit(self.run, generation_id, payload)

    def run(self, generation_id, payload):
        try:
            self.store.execute("UPDATE generations SET status='running' WHERE id=?", (generation_id,))
            self.graph.invoke(payload, self.config(generation_id))
            snapshot = self.graph.get_state(self.config(generation_id))
            review = next((i.value for t in snapshot.tasks for i in t.interrupts), None)
            status = ('waiting_integration' if review and review['kind'] == 'integration' else
                      'needs_review' if review else 'rejected' if snapshot.values.get('rejected') else 'completed')
            error = None
            message = {'waiting_integration': 'Đã lưu bố cục; đang chờ worker dựng 3D.',
                 'needs_review': 'Cần bạn kiểm tra để tiếp tục.', 'rejected': 'Bản nháp đã được từ chối.',
                 'completed': 'Bản nháp đã hoàn tất, sẵn sàng xuất bản.'}[status]
        except Exception:
            # No provider body, prompts, private metadata or traceback in public events.
            message = 'Chưa hoàn thành bước hiện tại. Kiểm tra OpenAI hoặc worker rồi thử lại; các bước đã lưu được giữ nguyên.'
            status, error = 'failed', message
        with self.store.lock:
            self.store.execute('UPDATE generations SET status=?,error=? WHERE id=?', (status, error, generation_id))
            node = snapshot.next[0] if status in ('needs_review', 'waiting_integration') and snapshot.next else 'workflow'
            self.store.emit(generation_id, node, status, message)
            self.active.discard(generation_id)

    def publish(self, owner, generation_id, request_id):
        def operation():
            current = self.generation(owner, generation_id)
            package = current['package']
            if current['status'] != 'completed' or not package or not package['approved']:
                raise HTTPException(409, 'Tour chưa được duyệt và hoàn tất.')
            if not package.get('music'):
                raise HTTPException(422, 'Cần nhạc nền có nguồn/quyền sử dụng trước khi xuất bản.')
            previous = self.store.rows('SELECT id FROM published WHERE generation=?', (generation_id,))
            if previous:
                return {'id': previous[0]['id']}
            public_id = uid()
            package = json.loads(json.dumps(package))
            package['published_at'] = now()
            package['public_id'] = public_id
            # Publish only approved artifacts, never raw description/missing fields.
            assets = self.store.assets(current['project_id'])
            allowed = {r['asset_id'] for r in package['rooms']} | {package['model']['asset_id'], package['music']['id']}
            allowed |= {a['asset_id'] for a in package['narration']['audio']}
            if not allowed <= {a['id'] for a in assets}:
                raise HTTPException(409, 'Tour thiếu asset đã kiểm chứng.')
            for asset in assets:
                if asset['id'] in allowed:self.store.verify_asset(asset)
            package['assets'] = [{k: a[k] for k in ('id', 'kind', 'mime', 'name')} for a in assets if a['id'] in allowed]
            package = PublishedTour.model_validate(package).model_dump()
            self.store.execute('INSERT INTO published VALUES(?,?,?,?)', (public_id, current['project_id'], generation_id, json.dumps(package, ensure_ascii=False)))
            return {'id': public_id}
        return self.store.action(owner, request_id, {'publish': generation_id}, operation)

    def answer(self, owner, package, data):
        if self.provider is None:
            raise HTTPException(503, 'Cần cấu hình OpenAI ở backend cho trợ lý xem tour.')
        if data.checkpoint_id not in {r['checkpoint_id'] for r in package['rooms']}:
            raise HTTPException(422, 'Checkpoint không thuộc tour đã xuất bản.')
        payload = data.model_dump_json()
        key = (owner, package['public_id'], data.request_id)
        with self.store.lock:
            previous = self.store.rows('SELECT * FROM viewer_requests WHERE owner=? AND tour=? AND request=?', key)
            if previous:
                row = previous[0]
                if row['payload'] != payload:
                    raise HTTPException(409, 'Request ID đã dùng cho câu hỏi khác.')
                if row['status'] == 'completed':
                    return json.loads(row['result'])
                raise HTTPException(409, 'Câu hỏi này đã được gửi. Đợi kết quả hoặc gửi câu hỏi mới.')
            requests = self.store.rows('SELECT status FROM viewer_requests WHERE owner=? AND tour=?', key[:2])
            if len(requests) >= 20 or any(r['status'] == 'running' for r in requests):
                raise HTTPException(429, 'Hãy đợi câu trả lời; mỗi phiên có tối đa 20 câu hỏi cho tour này.')
            self.store.execute('INSERT INTO viewer_requests VALUES(?,?,?,?,?,NULL)', (*key, payload, 'running'))
        try:
            result = ViewerAnswer.model_validate(self.provider.answer(package, data.question, data.checkpoint_id)).model_dump()
            if result['navigate_to'] not in {None, *(r['checkpoint_id'] for r in package['rooms'])}:
                raise ValueError('Invalid navigation target')
        except Exception:
            self.store.execute("UPDATE viewer_requests SET status='failed' WHERE owner=? AND tour=? AND request=?", key)
            raise HTTPException(502, 'OpenAI chưa trả lời được. Bạn vẫn có thể khám phá tour và đọc lời giới thiệu.') from None
        self.store.execute("UPDATE viewer_requests SET status='completed',result=? WHERE owner=? AND tour=? AND request=?", (json.dumps(result), *key))
        return result
