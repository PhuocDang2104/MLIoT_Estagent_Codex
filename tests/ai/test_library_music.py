from fastapi.testclient import TestClient
from tests.ai.test_creator import app, draft, post, settled, spatial, HEADERS
from tests.ai.creator_fixtures import Provider, Worker, wav


def test_late_music_no_paid_rerun_public_library_and_snapshot_freeze(tmp_path):
    provider=Provider()
    with TestClient(app(tmp_path,provider,Worker())) as client:
        pid=draft(client)
        assert client.get('/api/studio-tours').json()==[]
        gid=post(client,f'/projects/{pid}/generations',{'request_id':'start-late-music'}).json()['id']
        g=settled(client,gid)
        post(client,f'/generations/{gid}/review',spatial(g))
        assert settled(client,gid)['review']['kind']=='final'
        post(client,f'/generations/{gid}/review',{'kind':'final','decision':'approve','request_id':'approve-final'})
        assert settled(client,gid)['status']=='completed'
        assert post(client,f'/generations/{gid}/publish',{'request_id':'no-music-yet'}).status_code==422
        calls=list(provider.calls)
        track=post(client,f'/projects/{pid}/music/placeholder',{'request_id':'placeholder-demo'})
        assert track.status_code==200,track.text
        assert track.json()['duration']==75 and 'CC BY 4.0' in track.json()['credit']
        assert post(client,f'/projects/{pid}/music/placeholder',{'request_id':'placeholder-demo'}).json()==track.json()
        replacement=client.post(f'/api/studio/projects/{pid}/assets?kind=music&name=test.wav&credit=Synthetic-test',content=wav(),headers=HEADERS)
        assert replacement.status_code==201,replacement.text
        assert sum(a['kind']=='music' for a in client.get('/api/studio/projects/'+pid).json()['assets'])==1
        published=post(client,f'/generations/{gid}/publish',{'request_id':'publish-with-music'})
        assert published.status_code==200,published.text
        tid=published.json()['id']
        package=client.get('/api/studio-tours/'+tid).json()
        assert package['music']['id']==replacement.json()['id'] and provider.calls==calls
        assert post(client,f'/projects/{pid}/music/placeholder',{'request_id':'after-published'}).status_code==409
        assert client.delete(f"/api/studio/projects/{pid}/assets/{replacement.json()['id']}",headers=HEADERS).status_code==409
        client.cookies.clear()
        library=client.get('/api/studio-tours').json()
        assert len(library)==1 and library[0]['viewer_url']==f'/studio-tour.html?id={tid}'
        assert 'description' not in library[0] and 'owner' not in library[0]
        assert client.get(library[0]['thumbnail_url']).status_code==200
        assert client.get('/api/studio-tours/'+tid).json()==package
