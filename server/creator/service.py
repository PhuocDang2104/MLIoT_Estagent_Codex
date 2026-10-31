import json
import sqlite3
from .runtime import RuntimeLock, DurableQueue
from fastapi import HTTPException
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from .graph import build_graph, validate_review
from .store import Store, uid, now
from .package import PublishedTour
from .models import ViewerAnswer
from .edits import validate_plan
from .worker import HTTPGeometryWorker, WorkerPending


class Creator:
    """One fenced process, one durable dispatcher; checkpoints survive restarts."""
    def __init__(self, root, provider=None, worker=None, env=None, *, object_storage=None, storage_limits=None):
        self.runtime_lock = RuntimeLock(root)
        try:
            self.store = Store(root, object_storage=object_storage, storage_limits=storage_limits)
        except BaseException:
            self.runtime_lock.close()
            raise
        self.provider = provider
        self.connection = None
        try:
            self.worker = worker or (HTTPGeometryWorker(env, self.store) if env and env.get('STUDIO_GEOMETRY_URL') else None)
            self.connection = sqlite3.connect(root / 'graph.sqlite', check_same_thread=False)
            (root / 'graph.sqlite').chmod(0o600)
            self.graph = build_graph(provider, SqliteSaver(self.connection), self.store.emit,
                self.store.content, self.store.write_audio, self.store.write_model, self.worker)
            # A crash after checkpoint commit but before metadata commit must not
            # strand an already persisted human interrupt or completed package.
            for generation_id in self.store.interrupted:
                snapshot = self.graph.get_state(self.config(generation_id))
                review = next((i.value for t in snapshot.tasks for i in t.interrupts), None)
                status = ('waiting_integration' if review and review['kind'] == 'integration'
                          else 'needs_review' if review else 'rejected' if not snapshot.next and snapshot.values.get('rejected')
                          else 'completed' if not snapshot.next and snapshot.values.get('package') else None)
                if status:
                    with self.store.transaction():
                        self.store.execute('UPDATE generations SET status=?,error=NULL,revision=revision+1 WHERE id=?', (status,generation_id))
                        self.store.execute("UPDATE jobs SET status='done' WHERE generation=?", (generation_id,))
                        self.store.emit(generation_id,'workflow',status,'Recovered from a checkpoint after the process stopped.')
        except BaseException:
            if self.connection is not None:
                self.connection.close()
            self.store.db.close()
            self.runtime_lock.close()
            raise
        self.queue = DurableQueue(self.store, self.run)
        self.queue.thread.start()

    def close(self):
        self.queue.close()
        self.connection.close()
        self.store.db.close()
        self.runtime_lock.close()

    def config(self, generation_id):
        return {'configurable': {'thread_id': generation_id}, 'recursion_limit': 100}

    def generation(self, owner, generation_id):
        rows = self.store.rows('SELECT * FROM generations WHERE id=?', (generation_id,))
        if not rows:
            raise HTTPException(404, 'Tour generation not found.')
        self.store.project(owner, rows[0]['project'])
        row = rows[0]
        snapshot = self.graph.get_state(self.config(generation_id))
        values = snapshot.values
        review = next((i.value for t in snapshot.tasks for i in t.interrupts), None)
        return {'id': generation_id, 'project_id': row['project'], 'status': row['status'],
                'error': row['error'], 'attempts': row['attempts'], 'revision': row['revision'],
                'parent_id': row['parent'], 'review': review,
                'brief': values.get('brief'), 'rooms': values.get('rooms', []),
                'connections': values.get('connections', []), 'script': values.get('script'),
                'model': values.get('model'), 'package': values.get('package'),
                'modeling_plan':values.get('modeling_plan'), 'plan_attempts':values.get('plan_attempts',0),
                'observations': values.get('observations', []),
                'events': self.store.events(generation_id)}

    def project(self, owner, project_id):
        return {**self.store.project(owner, project_id), 'assets': self.store.assets(project_id),
                'generations': self.store.rows('SELECT id,status,error FROM generations WHERE project=? ORDER BY rowid DESC', (project_id,)),
                'published': self.store.rows('SELECT id,generation FROM published WHERE project=? ORDER BY rowid DESC', (project_id,))}

    def create(self, owner, data):
        def operation():
            if len(self.store.rows('SELECT id FROM projects WHERE owner=?', (owner,))) >= 10:
                raise HTTPException(429, 'This session has reached the limit of 10 projects.')
            project = {'id': uid(), 'created_at': now(), **data.model_dump(exclude={'request_id'})}
            self.store.execute('INSERT INTO projects VALUES(?,?,?)', (project['id'], owner, json.dumps(project, ensure_ascii=False)))
            return {'id': project['id']}
        return self.store.action(owner, data.request_id, {'create': data.model_dump()}, operation)

    def start(self, owner, project_id, request_id):
        self.queue.ensure_ready()
        def operation():
            if self.provider is None:
                raise HTTPException(503, 'Configure OpenAI on the backend to generate a tour.')
            project = self.store.project(owner, project_id)
            assets = self.store.assets(project_id)
            panoramas = [a for a in assets if a['kind'] == 'panorama']
            if not 1 <= len(panoramas) <= 12:
                raise HTTPException(422, 'Between 1 and 12 panorama images are required.')
            runs = self.store.rows('SELECT status FROM generations WHERE project=?', (project_id,))
            if runs:
                raise HTTPException(409, 'Inputs are locked during tour generation. Create a new project to change them.')
            if len(self.store.rows("SELECT id FROM generations WHERE status IN ('queued','running')")) >= 8:
                raise HTTPException(429, 'The queue is full. Please try again later.')
            generation_id = uid()
            self.store.execute('INSERT INTO generations(id,project,status,attempts) VALUES(?,?,?,1)', (generation_id, project_id, 'queued'))
            self.enqueue(generation_id, {'project': {**project, 'generation_id': generation_id}, 'assets': assets})
            return {'id': generation_id}
        result = self.store.action(owner, request_id, {'start': project_id}, operation)
        return result

    def resume(self, owner, generation_id, review):
        self.queue.ensure_ready()
        def operation():
            current = self.generation(owner, generation_id)
            if current['status'] != 'needs_review' or not current['review'] or current['review']['kind'] != review.kind:
                raise HTTPException(409, 'The review step changed. Reload the data.')
            try:
                validate_review(review, current['rooms'],current.get('modeling_plan'),current.get('plan_attempts',0))
                if review.kind == 'final' and review.scripts:
                    allowed = {'description', *(r['asset_id'] for r in current['rooms'])}
                    if any(not set(x.sources) <= allowed for x in review.scripts):
                        raise ValueError('Invalid evidence')
            except ValueError as error:
                raise HTTPException(422, str(error)) from None
            if review.revision is not None and review.revision != current['revision']:
                raise HTTPException(409, 'Phi?n b?n ?? thay ??i. T?i l?i d? li?u.')
            self.store.execute("UPDATE generations SET status='queued',error=NULL,revision=revision+1 WHERE id=?", (generation_id,))
            self.enqueue(generation_id, Command(resume=review.model_dump()))
            return {'id': generation_id}
        result = self.store.action(owner, review.request_id, {'review': generation_id, **review.model_dump()}, operation)
        return result

    def retry(self, owner, generation_id, request_id):
        self.queue.ensure_ready()
        def operation():
            current = self.generation(owner, generation_id)
            if self.provider is None:
                raise HTTPException(503, 'Configure OpenAI on the backend.')
            integration_ready = current['status'] == 'waiting_integration' and self.worker is not None
            if not integration_ready and (current['status'] != 'failed' or current['review']):
                raise HTTPException(409, 'This tour generation does not need to run again.')
            if current['attempts'] >= 3:
                raise HTTPException(429, 'All 3 attempts have been used. Check the configuration before creating a new project.')
            self.store.execute("UPDATE generations SET status='queued',error=NULL,attempts=attempts+1 WHERE id=?", (generation_id,))
            snapshot = self.graph.get_state(self.config(generation_id))
            if any(i.value.get('kind') == 'integration' for t in snapshot.tasks for i in t.interrupts) and self.worker is not None:
                payload = Command(resume=True)
            elif snapshot.values:
                payload = None
            else:
                row = self.store.rows('SELECT project FROM generations WHERE id=?', (generation_id,))[0]
                jobs = self.store.rows('SELECT payload FROM jobs WHERE generation=?', (generation_id,))
                saved = json.loads(jobs[0]['payload']) if jobs else {}
                payload = saved.get('input') or {'project': {**self.store.project(owner, row['project']), 'generation_id': generation_id},
                                               'assets': self.store.assets(row['project'])}
            self.enqueue(generation_id, payload)
            return {'id': generation_id}
        result = self.store.action(owner, request_id, {'retry': generation_id}, operation)
        return result

    def enqueue(self, generation_id, payload):
        # Called inside the same transaction as generation/action state.
        DurableQueue.put(self.store, generation_id, payload)

    def run(self, generation_id, payload):
        try:
            self.store.execute("UPDATE generations SET status='running' WHERE id=?", (generation_id,))
            stream = self.graph.stream(payload, self.config(generation_id), stream_mode='updates')
            try:
                for _ in stream:
                    if self.queue.stop.is_set():
                        break
            finally:
                stream.close()
            if self.queue.stop.is_set():
                with self.store.transaction():
                    self.store.execute("UPDATE generations SET status='queued' WHERE id=?", (generation_id,))
                    self.store.execute("UPDATE jobs SET status='queued',payload=? WHERE generation=?", (json.dumps({'input': None}), generation_id))
                return
            snapshot = self.graph.get_state(self.config(generation_id))
            review = next((i.value for t in snapshot.tasks for i in t.interrupts), None)
            status = ('waiting_integration' if review and review['kind'] == 'integration' else
                      'needs_review' if review else 'rejected' if snapshot.values.get('rejected') else 'completed')
            error = None
            message = {'waiting_integration': 'Layout saved; waiting for the 3D geometry worker.',
                 'needs_review': 'Your review is needed to continue.', 'rejected': 'The draft was rejected.',
                 'completed': 'The draft is complete and ready to publish.'}[status]
        except WorkerPending:
            # Geometry polling is read-only and durable; no OpenAI node is repeated.
            with self.store.transaction():
                self.store.execute("UPDATE generations SET status='queued' WHERE id=?", (generation_id,))
                self.store.execute("UPDATE jobs SET status='queued',payload=?,available_at=? WHERE generation=?",
                    (json.dumps({'input':None}), self.queue.clock()+5, generation_id))
            return
        except Exception:
            # No provider body, prompts, private metadata or traceback in public events.
            message = 'The current step is incomplete. Check OpenAI or the worker and retry; saved steps are preserved.'
            status, error = 'failed', message
        with self.store.transaction():
            self.store.execute('UPDATE generations SET status=?,error=?,revision=revision+1 WHERE id=?', (status, error, generation_id))
            self.store.execute("UPDATE jobs SET status='done' WHERE generation=?", (generation_id,))
            node = snapshot.next[0] if status in ('needs_review', 'waiting_integration') and snapshot.next else 'workflow'
            self.store.emit(generation_id, node, status, message)


    def publish(self, owner, generation_id, request_id):
        def operation():
            current = self.generation(owner, generation_id)
            package = current['package']
            if current['status'] != 'completed' or not package or not package['approved']:
                raise HTTPException(409, 'The tour has not been approved and completed.')
            previous = self.store.rows('SELECT id FROM published WHERE generation=?', (generation_id,))
            if previous:
                return {'id': previous[0]['id']}
            public_id = uid()
            package = json.loads(json.dumps(package))
            package['published_at'] = now()
            package['public_id'] = public_id
            # Publish only approved artifacts, never raw description/missing fields.
            assets = self.store.assets(current['project_id'])
            package['music'] = next((a for a in assets if a['kind'] == 'music'), None)
            if not package['music']:
                raise HTTPException(422, 'Background music with a source and usage rights is required before publishing.')
            allowed = {r['asset_id'] for r in package['rooms']} | {package['model']['asset_id'], package['music']['id']}
            allowed |= {a['asset_id'] for a in package['narration']['audio']}
            if not allowed <= {a['id'] for a in assets}:
                raise HTTPException(409, 'The tour is missing a verified asset.')
            for asset in assets:
                if asset['id'] in allowed:self.store.verify_asset(asset)
            package['assets'] = [{k: a[k] for k in ('id', 'kind', 'mime', 'name')} for a in assets if a['id'] in allowed]
            package = PublishedTour.model_validate(package).model_dump()
            self.store.execute('INSERT INTO published VALUES(?,?,?,?)', (public_id, current['project_id'], generation_id, json.dumps(package, ensure_ascii=False)))
            return {'id': public_id}
        return self.store.action(owner, request_id, {'publish': generation_id}, operation)

    def propose_edit(self, owner, generation_id, data):
        fresh = False
        def reserve():
            nonlocal fresh
            current = self.generation(owner, generation_id)
            if current['revision'] != data.revision or current['status'] not in ('completed', 'needs_review', 'waiting_integration'):
                raise HTTPException(409, 'The draft has changed or is running. Reload and retry.')
            if not current['rooms']:
                raise HTTPException(409, 'Wait for space identification before editing through chat.')
            if self.provider is None or not hasattr(self.provider, 'edit'):
                raise HTTPException(503, 'OpenAI is not configured for editing.')
            if len(self.store.rows('SELECT id FROM edits WHERE generation=?', (generation_id,))) >= 20:
                raise HTTPException(429, 'This draft has reached the limit of 20 proposals.')
            if self.store.rows("SELECT id FROM edits WHERE owner=? AND status='running'", (owner,)):
                raise HTTPException(409, 'Wait for the previous proposal to finish.')
            edit_id = uid()
            self.store.execute('INSERT INTO edits VALUES(?,?,?,?,?,?)',
                (edit_id, generation_id, owner, data.revision, json.dumps({'text':data.text}), 'running'))
            fresh = True
            return {'id': edit_id}
        result = self.store.action(owner, data.request_id, {'edit':generation_id, **data.model_dump()}, reserve)
        row = self.store.rows('SELECT * FROM edits WHERE id=? AND owner=?', (result['id'], owner))[0]
        if not fresh:
            if row['status'] in ('pending', 'applied'):
                return {'id':row['id'], 'revision':row['revision'], **json.loads(row['data']), 'status':row['status']}
            raise HTTPException(409, 'The proposal is processing or failed. Send a new request if needed.')
        try:
            state = self.graph.get_state(self.config(generation_id)).values
            plan, route, changed = validate_plan(self.provider.edit(state, data.text), state)
        except Exception:
            self.store.execute("UPDATE edits SET status='failed' WHERE id=?", (row['id'],))
            raise HTTPException(502, 'Could not create a valid proposal. Your draft is preserved.') from None
        value = {'text':data.text, 'plan':plan, 'route':route, 'can_apply':changed}
        self.store.execute("UPDATE edits SET status='pending',data=? WHERE id=?", (json.dumps(value, ensure_ascii=False), row['id']))
        return {'id':row['id'], 'revision':row['revision'], 'status':'pending', **value}

    def apply_edit(self, owner, generation_id, edit_id, data):
        self.queue.ensure_ready()
        def operation():
            current = self.generation(owner, generation_id)
            rows = self.store.rows('SELECT * FROM edits WHERE id=? AND owner=? AND generation=?', (edit_id, owner, generation_id))
            if not rows:
                raise HTTPException(404, 'Proposal not found.')
            row = rows[0]
            if row['status'] != 'pending' or row['revision'] != data.revision or current['revision'] != data.revision:
                raise HTTPException(409, 'The proposal is outdated or already applied. Reload the draft.')
            if current['status'] not in ('completed', 'needs_review', 'waiting_integration'):
                raise HTTPException(409, 'Wait for the current run to finish.')
            state = json.loads(json.dumps(self.graph.get_state(self.config(generation_id)).values))
            plan, route, changed = validate_plan(json.loads(row['data'])['plan'], state)
            if not changed:
                raise HTTPException(422, 'This proposal has no changes to apply.')
            pid = current['project_id']
            if len(self.store.rows('SELECT id FROM generations WHERE project=?', (pid,))) >= 20:
                raise HTTPException(429, 'This project has reached the limit of 20 versions.')
            if len(self.store.rows("SELECT id FROM generations WHERE status IN ('queued','running')")) >= 8:
                raise HTTPException(429, 'The queue is full.')
            gid = uid()
            state.update(entry='edit', edit_plan=plan, edit_route=route)
            state['project'] = {**state['project'], 'generation_id':gid}
            self.store.execute("INSERT INTO generations(id,project,status,attempts,parent) VALUES(?,?,'queued',1,?)", (gid,pid,generation_id))
            self.store.execute("UPDATE edits SET status='applied' WHERE id=?", (edit_id,))
            self.store.execute('UPDATE generations SET revision=revision+1 WHERE id=?', (generation_id,))
            self.enqueue(gid, state)
            return {'id':gid, 'parent_id':generation_id}
        return self.store.action(owner, data.request_id, {'apply':edit_id, 'generation':generation_id, **data.model_dump()}, operation)

    def answer(self, owner, package, data):
        if self.provider is None:
            raise HTTPException(503, 'Configure OpenAI on the backend to enable the tour assistant.')
        if data.checkpoint_id not in {r['checkpoint_id'] for r in package['rooms']}:
            raise HTTPException(422, 'This checkpoint does not belong to the published tour.')
        payload = data.model_dump_json()
        key = (owner, package['public_id'], data.request_id)
        with self.store.lock:
            previous = self.store.rows('SELECT * FROM viewer_requests WHERE owner=? AND tour=? AND request=?', key)
            if previous:
                row = previous[0]
                if row['payload'] != payload:
                    raise HTTPException(409, 'This request ID was already used for another question.')
                if row['status'] == 'completed':
                    return json.loads(row['result'])
                raise HTTPException(409, 'This question has already been sent. Wait for the result or send a new question.')
            requests = self.store.rows('SELECT status FROM viewer_requests WHERE owner=? AND tour=?', key[:2])
            if len(requests) >= 20 or any(r['status'] == 'running' for r in requests):
                raise HTTPException(429, 'Please wait for the answer; each session allows up to 20 questions for this tour.')
            self.store.execute('INSERT INTO viewer_requests VALUES(?,?,?,?,?,NULL)', (*key, payload, 'running'))
        try:
            result = ViewerAnswer.model_validate(self.provider.answer(package, data.question, data.checkpoint_id)).model_dump()
            if result['navigate_to'] not in {None, *(r['checkpoint_id'] for r in package['rooms'])}:
                raise ValueError('Invalid navigation target')
        except Exception:
            self.store.execute("UPDATE viewer_requests SET status='failed' WHERE owner=? AND tour=? AND request=?", key)
            raise HTTPException(502, 'OpenAI could not respond. You can still explore the tour and read the introduction.') from None
        self.store.execute("UPDATE viewer_requests SET status='completed',result=? WHERE owner=? AND tour=? AND request=?", (json.dumps(result), *key))
        return result
