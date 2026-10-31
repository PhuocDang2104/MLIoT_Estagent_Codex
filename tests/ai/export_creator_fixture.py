"""Explicit schema/contract fixture generator. Synthetic media never represents a real house."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from fastapi.testclient import TestClient
from server.creator.package import PublishedTour
from tests.ai.creator_fixtures import Provider, Worker
from tests.ai.test_creator import app, draft, post, settled, spatial


def main():
    root=Path(__file__).resolve().parents[2]/'fixtures'
    target=root/'studio-example'
    target.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='estagent-schema-') as directory:
        with TestClient(app(Path(directory),Provider(),Worker())) as client:
            pid=draft(client,music=True)
            gid=post(client,f'/projects/{pid}/generations',{'request_id':'start-project'}).json()['id']
            g=settled(client,gid)
            post(client,f'/generations/{gid}/review',spatial(g))
            settled(client,gid)
            post(client,f'/generations/{gid}/review',{'kind':'final','decision':'approve','request_id':'approve-final'})
            assert settled(client,gid)['status']=='completed'
            public=post(client,f'/generations/{gid}/publish',{'request_id':'publish-fixture'}).json()['id']
            package=client.get('/api/studio-tours/'+public).json()
            (target/'studio-tour.json').write_text(json.dumps(package,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    schema={'$schema':'https://json-schema.org/draft/2020-12/schema',**PublishedTour.model_json_schema()}
    (root/'studio-tour.schema.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Exported published Creator schema + explicitly synthetic contract fixture')


if __name__=='__main__':
    main()
