"""Local API/SQLite regressions for description-first draft creation; no live AI."""
import json
from pathlib import Path

import httpx
import jsonschema
import pytest
from fastapi.testclient import TestClient
from openai import APIError, RateLimitError

from tests.ai.test_tours import app_at, create, edit_body, post, session, upload, HEADERS


DESCRIPTION = 'Căn hộ 2PN Quận 7, hướng Đông Nam. Ban công thoáng.'


@pytest.mark.parametrize('placeholder', [None, 'My space', 'Untitled tour', 'Không gian của tôi'])
def test_description_seeds_keyless_draft_and_survives_publish(tmp_path, placeholder):
    with TestClient(app_at(tmp_path)) as client:
        session(client)
        assert client.get('/api/tours/session').json()['configured'] is False
        assets=[upload(client), upload(client, 'teal'), upload(client, 'orange')]
        body={'asset_ids':[a['id'] for a in assets], 'text':DESCRIPTION,
              'locale':'vi', 'request_id':'description-draft'}
        if placeholder is not None:body['title']=placeholder
        response=post(client, '/drafts', body)
        assert response.status_code==200,response.text
        doc=response.json()
        assert doc['title']=='Căn hộ 2PN Quận 7'
        assert doc['locale']=='vi'
        assert [scene['name'] for scene in doc['scenes']]==['Tổng quan','Góc nhìn 2','Góc nhìn 3']
        assert doc['scenes'][0]['description']==DESCRIPTION
        assert all(scene['projection']=='photo' and scene['coverage_degrees'] is None for scene in doc['scenes'])
        assert all('phòng ngủ' not in scene['name'] for scene in doc['scenes'])
        assert post(client,'/drafts',body).json()==doc
        assert post(client,'/drafts',body|{'text':'Different brief'}).status_code==409
        assert client.get(f'/api/tours/drafts/{doc["id"]}/messages').json()==[
            {'role':'user','text':DESCRIPTION,'attachments':body['asset_ids']}]
        route=f'/drafts/{doc["id"]}'
        assert post(client,route+'/review',{'revision':1}).status_code==200
        published=post(client,route+'/publish',{'revision':1}).json()
        jsonschema.validate(published,json.loads(Path('fixtures/tour.schema.json').read_text()))
        client.cookies.clear()
        assert client.get(f'/api/tours/published/{published["id"]}').json()==published
        assert published['title']==doc['title'] and published['locale']=='vi'
        assert client.get(published['scenes'][0]['image_url']).status_code==200


def test_explicit_title_locale_and_saved_edits_are_never_replaced(tmp_path):
    with TestClient(app_at(tmp_path)) as client:
        session(client);asset=upload(client)
        body={'asset_ids':[asset['id']], 'text':DESCRIPTION, 'title':'My curated listing',
              'locale':'en', 'request_id':'explicit-identity'}
        doc=post(client,'/drafts',body).json()
        assert doc['title']=='My curated listing' and doc['locale']=='en'
        edit=edit_body(doc);edit['title']='A later edit';edit['scenes'][0]['description']='A reviewed description.'
        saved=client.put(f'/api/tours/drafts/{doc["id"]}',json=edit,headers=HEADERS).json()
        # Retry the original create request returns the saved draft, not fresh defaults.
        assert post(client,'/drafts',body).json()==saved
        assert saved['title']=='A later edit' and saved['revision']==2


@pytest.mark.parametrize('text,locale,title', [
    (DESCRIPTION,'en','Căn hộ 2PN Quận 7'),
    ('A bright apartment, near the park.','en','A bright apartment'),
    ('','en','Your photo tour'),
])
def test_omitted_locale_and_title_have_safe_defaults(tmp_path,text,locale,title):
    with TestClient(app_at(tmp_path)) as client:
        session(client);asset=upload(client)
        doc=post(client,'/drafts',{'asset_ids':[asset['id']],'text':text,'request_id':'auto-defaults'}).json()
        assert doc['locale']==locale and doc['title']==title
        assert doc['scenes'][0]['description']


def test_long_description_stays_within_existing_manifest_limits(tmp_path):
    with TestClient(app_at(tmp_path)) as client:
        session(client);asset=upload(client)
        text='x'*2000
        response=post(client,'/drafts',{'asset_ids':[asset['id']],'text':text,'request_id':'long-description'})
        assert response.status_code==200,response.text
        assert len(response.json()['title'])==150
        assert response.json()['scenes'][0]['description']==text


@pytest.mark.parametrize('locale', ['en','vi'])
def test_keyless_creator_and_viewer_errors_are_english_and_nontechnical(tmp_path,locale):
    with TestClient(app_at(tmp_path)) as client:
        session(client);doc=create(client,[upload(client)])
        route=f'/drafts/{doc["id"]}'
        post(client,route+'/review',{'revision':1})
        published=post(client,route+'/publish',{'revision':1}).json()
        for path in [route+'/chat',f'/published/{published["id"]}/chat']:
            response=post(client,path,{'text':'Tell me more','locale':locale,'revision':1,'request_id':'safe-error'})
            assert response.status_code==503
            detail=response.json()['detail']
            assert 'The assistant' in detail
            assert all(term not in detail for term in ['OPENAI','API_KEY','quota',' / ','configure'])
        assert client.get('/api/tours'+route).json()==doc
        assert client.get(f'/api/tours/published/{published["id"]}').json()==published


@pytest.mark.parametrize('locale',['en','vi'])
@pytest.mark.parametrize('failure', ['rate','provider','invalid'])
def test_provider_failures_keep_status_and_hide_internal_details(tmp_path,locale,failure):
    def failing(context):
        if failure=='invalid':return {'reply':'untrusted malformed response'}
        request=httpx.Request('POST','https://api.openai.com/v1/responses')
        if failure=='rate':raise RateLimitError('secret upstream quota detail',response=httpx.Response(429,request=request),body=None)
        raise APIError('secret upstream API_KEY detail',request=request,body=None)
    with TestClient(app_at(tmp_path,failing)) as client:
        session(client);doc=create(client,[upload(client)])
        route=f'/drafts/{doc["id"]}'
        response=post(client,route+'/chat',{'text':'Help','locale':locale,'revision':1,'request_id':'provider-error'})
        assert response.status_code==(429 if failure=='rate' else 502)
        detail=response.json()['detail']
        assert 'The assistant' in detail
        assert all(term not in detail for term in ['secret','quota','API_KEY',' / '])
        assert client.get('/api/tours'+route).json()==doc
