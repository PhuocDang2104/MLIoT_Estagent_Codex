"""Exercise actual LangGraph routing/checkpoints. Model and paid network are fixtures."""
import json
import uuid
import httpx
import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver
from server.assistant.graph import build_graph, Extraction, LABELS
from server.assistant.app import create_app, COOKIE

def voice_fixture_env(tmp_path):
    return {'OPENAI_API_KEY':'fixture-secret','ASSISTANT_ORIGIN':'http://testserver',
        'API_LIMITS_ENABLED':'1','API_LIMITS_DB':str(tmp_path/'limits.sqlite'),
        'API_LIMITS_AI_REQUESTS':'6','API_LIMITS_AI_WINDOW_SECONDS':'60',
        'API_LIMITS_AI_CONCURRENCY':'1','API_LIMITS_AI_ATTEMPTS':'50',
        'API_LIMITS_AI_ATTEMPT_WINDOW_SECONDS':'3600'}

def extracted(intent='answer',clarification=None,clear_fields=None,**patch):
    return Extraction.model_validate({'intent':intent,'patch':{k:patch.get(k) for k in LABELS},'clear_fields':clear_fields or [],'clarification':clarification})

def graph_runner():
    graph = build_graph(lambda s: Extraction.model_validate(json.loads(s['text'])),MemorySaver())
    config = {'configurable':{'thread_id':'test'}}
    def run(result): return graph.invoke({'text':result.model_dump_json(),'request_id':str(uuid.uuid4())},config)
    return run

def test_required_optional_defer_confirm_correct_and_clear():
    run = graph_runner()
    s = run(extracted(address='Quận 7, TP.HCM',area=85,bedrooms=0))
    assert s['stage'] == 'optional' and s['profile']['bedrooms'] == 0
    s = run(extracted('skip'))
    assert 'name' in s['deferred'] and s['awaiting'] == 'direction'
    s = run(extracted('skip_all'))
    assert s['stage'] == 'review' and not s['confirmed']
    s = run(extracted('confirm'))
    assert s['stage'] == 'complete' and s['confirmed']
    s = run(extracted(direction='SE',area=90))
    assert s['stage'] == 'review' and not s['confirmed'] and 'direction' not in s['deferred']
    s = run(extracted(clear_fields=['area']))
    assert s['stage'] == 'required' and s['awaiting'] == 'area'

def test_skip_required_does_not_claim_completion():
    run = graph_runner()
    s = run(extracted('skip_all',address='Hà Nội'))
    assert s['stage'] == 'required' and s['awaiting'] == 'area'
    assert not s['confirmed'] and 'area' not in s['deferred']

def test_ambiguity_and_inconsistent_patch_leave_profile_unchanged():
    run = graph_runner()
    run(extracted(area=85,bedrooms=2))
    s = run(extracted(area=90,clarification='Bạn nói 90 hay 95 m²?'))
    assert s['profile']['area'] == 85
    s = run(extracted(rooms=2,bathrooms=1))
    assert 'rooms' not in s['profile'] and s['errors']
    s = run(extracted(area=-1))
    assert s['profile']['area'] == 85

def test_help_keeps_pending_field_and_does_not_skip():
    run = graph_runner()
    run(extracted(address='Đà Nẵng'))
    s = run(extracted('help'))
    assert s['awaiting'] == 'area' and not s['deferred']

def test_configurable_required_policy():
    graph = build_graph(lambda s: extracted(address='Hà Nội',area=80),MemorySaver(),required=('address','area'))
    s = graph.invoke({'text':'test','request_id':'test-policy'},{'configurable':{'thread_id':'policy'}})
    assert s['stage'] == 'optional' and s['awaiting'] == 'bedrooms'

def test_api_persistence_isolation_idempotency_and_origin(tmp_path):
    calls = []
    def interpret(state):
        assert state['awaiting'] == 'address'  # First short answer has the displayed question as context.
        calls.append(state['text'])
        return extracted(address='Quận 7',area=85,bedrooms=2)
    path = tmp_path/'state.sqlite'
    env = {'ASSISTANT_ORIGIN':'http://testserver'}
    with TestClient(create_app(db_path=path,extractor=interpret,env=env)) as client:
        assert client.get('/api/assistant/state').status_code == 200
        cookie = client.cookies.get(COOKIE)
        body = {'text':'Căn hộ của tôi','request_id':'request-one'}
        assert client.post('/api/assistant/turn',json=body).status_code == 403
        headers = {'Origin':'http://testserver'}
        result = client.post('/api/assistant/turn',json=body,headers=headers)
        assert result.status_code == 200 and result.json()['profile']['area'] == 85
        assert client.post('/api/assistant/turn',json=body,headers=headers).status_code == 200
        assert len(calls) == 1
        assert client.post('/api/assistant/turn',content='x'*65537,headers=headers).status_code == 413
        client.cookies.clear()
        assert client.get('/api/assistant/state').json()['profile'] == {}
        assert client.get('/.env.local').status_code == 404
    with TestClient(create_app(db_path=path,extractor=interpret,env=env)) as client:
        client.cookies.set(COOKIE,cookie,path='/api/assistant/')
        assert client.get('/api/assistant/state').json()['profile']['area'] == 85

@pytest.mark.parametrize('key', [None, '', '   \t\n'])
def test_no_key_is_honest(tmp_path, key):
    env = {} if key is None else {'OPENAI_API_KEY': key}
    with TestClient(create_app(db_path=tmp_path/'missing.sqlite',env=env)) as client:
        assert client.get('/api/assistant/state').json()['configured'] is False
        response = client.post('/api/assistant/turn',json={'text':'Xin chào','request_id':'no-key-request'},headers={'Origin':'http://127.0.0.1:5180'})
        assert response.status_code == 503
        assert 'OpenAI' in response.json()['error']
        voice = client.post('/api/assistant/voice', content='v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n', headers={'Origin':'http://127.0.0.1:5180','Content-Type':'application/sdp'})
        assert voice.status_code == 503 and 'OpenAI' in voice.json()['error']
        state = client.get('/api/assistant/state').json()
        assert state['profile'] == {} and state['history'] == []

def test_voice_transport_server_key_and_graph_owns_replies(tmp_path):
    async def upstream(request):
        assert request.headers['Authorization'] == 'Bearer fixture-secret'
        payload = (await request.aread()).decode()
        assert '"create_response": false' in payload
        assert '"model": "gpt-transcribe"' in payload
        return httpx.Response(200,text='v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n')
    app = create_app(db_path=tmp_path/'voice.sqlite',extractor=lambda s:extracted(),env=voice_fixture_env(tmp_path),voice_transport=httpx.MockTransport(upstream))
    with TestClient(app) as client:
        client.get('/api/assistant/state')
        result = client.post('/api/assistant/voice',content='v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n',headers={'Origin':'http://testserver','Content-Type':'application/sdp'})
        assert result.status_code == 200 and result.text.startswith('v=0')
        assert 'fixture-secret' not in result.text

def test_voice_error_does_not_expose_upstream_body(tmp_path):
    app = create_app(db_path=tmp_path/'badvoice.sqlite',env=voice_fixture_env(tmp_path),voice_transport=httpx.MockTransport(lambda r:httpx.Response(401,text='private upstream content')))
    with TestClient(app) as client:
        client.get('/api/assistant/state')
        response=client.post('/api/assistant/voice',content='v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n',headers={'Origin':'http://testserver','Content-Type':'application/sdp'})
        assert response.status_code == 502 and 'private' not in response.text
