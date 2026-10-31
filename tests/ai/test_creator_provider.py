import json
import httpx
import pytest
from openai import OpenAI
from server.creator.provider import OpenAIProvider
from tests.ai.creator_fixtures import png, wav


def response(value):
    return {'id':'resp_fixture','object':'response','created_at':1,'model':'fixture',
            'status':'completed','output':[{'id':'msg_fixture','type':'message',
            'role':'assistant','status':'completed','content':[{'type':'output_text',
            'text':json.dumps(value),'annotations':[]}]}]}


def test_openai_sdk_structured_text_vision_and_speech_with_one_server_key():
    requests=[]
    def transport(request):
        assert request.headers['authorization']=='Bearer fixture-key'
        body=json.loads(request.content)
        requests.append((request.url.path,body))
        if request.url.path.endswith('/audio/speech'):
            assert body['response_format']=='wav' and body['model']=='gpt-4o-mini-tts'
            return httpx.Response(200,content=wav(),headers={'Content-Type':'audio/wav'})
        assert body['store'] is False and body['max_output_tokens']==6000
        assert body['reasoning']=={'effort':'low'}
        assert body['text']['format']['strict'] is True
        if body['model']=='text-fixture':
            return httpx.Response(200,json=response({'summary':'Summary','facts':[], 'missing':[]}))
        assert body['input'][0]['content'][1]['image_url'].startswith('data:image/png;base64,')
        return httpx.Response(200,json=response({'label':'Room','room_type':'living',
            'summary':'Observed','facts':[{'text':'Window','source':'asset-fixture','provenance':'observed'}], 'uncertainty':[]}))
    with OpenAI(api_key='fixture-key',max_retries=0,timeout=30,
                http_client=httpx.Client(transport=httpx.MockTransport(transport))) as client:
        provider=OpenAIProvider(client,{'OPENAI_MODEL_TEXT':'text-fixture','OPENAI_MODEL_VISION':'vision-fixture'})
        project={'name':'Fixture','description':'Synthetic test','locale':'vi','voice':'coral'}
        assert provider.brief(project)['summary']=='Summary'
        assert provider.observe(project,{'id':'asset-fixture','mime':'image/png'},png())['label']=='Room'
        assert provider.speech(project,'Fixture')==wav()
    assert len(requests)==3


def test_refusal_is_not_a_successful_generation():
    value={'id':'resp_fixture','object':'response','created_at':1,'model':'fixture','status':'completed',
           'output':[{'id':'msg_fixture','type':'message','role':'assistant','status':'completed',
                      'content':[{'type':'refusal','refusal':'Cannot process'}]}]}
    with OpenAI(api_key='fixture',max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=value)))) as client:
        with pytest.raises(ValueError):
            OpenAIProvider(client,{}).brief({'name':'Fixture','description':'Synthetic','locale':'vi'})


def test_usage_cap_survives_provider_restart_and_contains_no_prompts(tmp_path):
    log=tmp_path/'usage.jsonl'
    calls=[]
    def transport(request):
        calls.append(request)
        return httpx.Response(200,json={**response({'summary':'ok','facts':[], 'missing':[]}),
            'usage':{'input_tokens':10,'output_tokens':5,'total_tokens':15}})
    env={'STUDIO_API_CALL_LIMIT':'1','STUDIO_USAGE_LOG':str(log)}
    with OpenAI(api_key='fixture-secret',http_client=httpx.Client(transport=httpx.MockTransport(transport))) as client:
        provider=OpenAIProvider(client,env)
        assert provider.modeling_model=='gpt-6-astra' and provider.modeling_effort=='high'
        assert provider.vision_model=='gpt-6.1-terra' and provider.text_model=='gpt-6.1-sol'
        provider.brief({'name':'Private property','description':'Private description','locale':'en'})
        with pytest.raises(ValueError,match='call limit'):
            OpenAIProvider(client,env).brief({'name':'Second','description':'No call expected','locale':'en'})
    assert len(calls)==1
    records=[json.loads(line) for line in log.read_text().splitlines()]
    assert records[-1]['usage']['total_tokens']==15
    assert 'Private' not in log.read_text() and 'fixture-secret' not in log.read_text()
