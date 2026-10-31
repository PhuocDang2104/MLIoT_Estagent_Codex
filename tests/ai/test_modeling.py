from copy import deepcopy
import json
import httpx
import pytest
from fastapi.testclient import TestClient
from openai import OpenAI
from server.creator.scene_plan import validate_plan
from server.creator.provider import OpenAIProvider
from tests.ai.creator_fixtures import Provider, Worker, png
from tests.ai.test_creator import app, draft, post, settled, spatial
from tests.ai.test_creator_provider import response
from tests.core.house_fixture import house_plan

ROOMS=[{'checkpoint_id':f'cp{i+1:02}'} for i in range(2)]
ASSETS=[{'id':f'image{i+1}','kind':'panorama','mime':'image/png'} for i in range(2)]


@pytest.mark.parametrize('defect',['overlap','capture','evidence','invention','scale','opening','fixture'])
def test_plan_rejects_invalid_geometry_and_evidence(defect):
    value=house_plan()
    if defect=='overlap': value['spaces'][1]['polygon']=deepcopy(value['spaces'][0]['polygon'])
    if defect=='capture': value['captures'][0]['position']['x']=25
    if defect=='evidence': value['fixtures'][0]['sources']=['unknown']
    if defect=='invention': value['captures'][0]['checkpoint_id']='cp09'
    if defect=='scale': value['status']='ready'
    if defect=='opening': value['spaces'][0]['openings'][0]['width']=8
    if defect=='fixture': value['fixtures'][0]['position']['x']=0
    with pytest.raises(ValueError): validate_plan(value,ROOMS,ASSETS)


def test_plan_accepts_qualified_plan_and_missing_plan_questions():
    assert validate_plan(house_plan(),ROOMS,ASSETS)['scale']=='assumed'
    value=house_plan();value.update(status='needs_clarification',spaces=[],captures=[],fixtures=[],questions=['Which doors connect these captures?'])
    assert validate_plan(value,ROOMS,ASSETS)['questions']
    value['questions']=[]
    with pytest.raises(ValueError): validate_plan(value,ROOMS,ASSETS)


class PlanningProvider(Provider):
    def modeling_plan(self, project, rooms, observations, assets, read_asset, clarification):
        self.calls.append('plan')
        result=house_plan([r['asset_id'] for r in rooms])
        if not clarification:
            result.update(status='needs_clarification',questions=['Confirm kitchen door connects to living room.'])
        return result


class PlannedWorker(Worker):
    requires_scene_plan=True
    def build(self,project,*args):
        assert project['modeling_plan']['status']=='provisional'
        return super().build(project,*args)


def test_clarification_loop_approval_and_no_repeated_observations(tmp_path):
    provider=PlanningProvider()
    with TestClient(app(tmp_path,provider,PlannedWorker())) as client:
        pid=draft(client)
        gid=post(client,f'/projects/{pid}/generations',{'request_id':'start-plan'}).json()['id']
        g=settled(client,gid)
        assert g['plan_attempts']==1
        assert post(client,f'/generations/{gid}/review',spatial(g)).status_code==422
        assert post(client,f'/generations/{gid}/review',{'request_id':'clarify-plan','kind':'spatial','decision':'revise',
            'clarification':'These rooms share the shown door. Use approximate dimensions.'}).status_code==202
        g=settled(client,gid)
        assert g['plan_attempts']==2 and g['modeling_plan']['status']=='provisional'
        review=spatial(g);review['request_id']='approve-revision'
        assert post(client,f'/generations/{gid}/review',review).status_code==422
        review['accept_approximate']=True
        assert post(client,f'/generations/{gid}/review',review).status_code==202
        g=settled(client,gid)
        assert g['review']['kind']=='final' and g['model']
        assert provider.calls.count('observe')==2 and provider.calls.count('plan')==2
        assert 'speech' not in provider.calls


def test_real_sdk_planner_loads_skill_and_floorplan():
    def transport(request):
        assert request.url.host=='api.openai.com' and request.url.path=='/v1/responses'
        body=json.loads(request.content)
        assert body['text']['format']['type']=='json_schema'
        assert body['text']['format']['strict'] is True
        assert 'Studio modeling agent template' in body['instructions']
        assert body['max_output_tokens']==12000 and body['store'] is False
        content=body['input'][0]['content']
        assert sum(item['type']=='input_image' for item in content)==3
        assert all(item['image_url'].startswith('data:image/jpeg;base64,') for item in content if item['type']=='input_image')
        assert any('floorplan' in x.get('text','') for x in content)
        return httpx.Response(200,json=response(house_plan()))
    with OpenAI(api_key='fixture',max_retries=0,http_client=httpx.Client(transport=httpx.MockTransport(transport))) as client:
        provider=OpenAIProvider(client,{})
        assets=ASSETS+[{'id':'floor','kind':'floorplan','mime':'image/png'}]
        result=provider.modeling_plan({'description':'Synthetic plan','locale':'en'},ROOMS,[],assets,lambda _:png(),'')
        assert result['spaces'][0]['id']=='r01'


def test_restart_connecting_automatic_worker_requires_new_plan_review(tmp_path):
    provider=PlanningProvider()
    with TestClient(app(tmp_path,provider)) as client:
        pid=draft(client)
        gid=post(client,f'/projects/{pid}/generations',{'request_id':'start-legacy'}).json()['id']
        g=settled(client,gid)
        assert post(client,f'/generations/{gid}/review',spatial(g)).status_code==202
        assert settled(client,gid)['status']=='waiting_integration'
        cookie=client.cookies.get('estagent_studio')
    with TestClient(app(tmp_path,provider,PlannedWorker())) as client:
        client.cookies.set('estagent_studio',cookie)
        assert post(client,f'/generations/{gid}/retry',{'request_id':'connect-blender'}).status_code==202
        g=settled(client,gid)
        assert g['review']['kind']=='spatial' and g['plan_attempts']==1
        assert g['model'] is None and provider.calls.count('observe')==2


def test_revision_limit_and_shared_wall_openings():
    from server.creator.graph import validate_review
    from server.creator.models import Review
    revision=Review(request_id='revision-cap',kind='spatial',decision='revise',clarification='Another dimension')
    with pytest.raises(ValueError,match='Three planning'):
        validate_review(revision,ROOMS,house_plan(),3)
    value=house_plan();value['spaces'][1]['openings']=[]
    with pytest.raises(ValueError,match='Shared walls'):
        validate_plan(value,ROOMS,ASSETS)
