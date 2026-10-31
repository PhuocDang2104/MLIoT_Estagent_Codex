"""Run local Studio using a key read from an external dotenv file, never copied."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def read_key(path, name):
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        key,sep,value=line.strip().removeprefix('export ').partition('=')
        if sep and key.strip().strip('\"\x27')==name:
            value=value.strip().strip('\"\x27')
            if value: return value
    raise ValueError('Requested API key entry is missing or empty')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file',type=Path,required=True)
    parser.add_argument('--key-name',default='openAIKey')
    parser.add_argument('--port',type=int,default=5180)
    parser.add_argument('--data-dir',type=Path,default=ROOT/'projects/local-live/work')
    parser.add_argument('--text-model',default='gpt-6.1-sol')
    parser.add_argument('--vision-model',default='gpt-6.1-terra')
    parser.add_argument('--modeling-model',default='gpt-6-astra')
    parser.add_argument('--modeling-effort',default='high')
    parser.add_argument('--tts-model',default='gpt-4o-mini-tts')
    parser.add_argument('--call-limit',type=int,default=40)
    parser.add_argument('--check-models',action='store_true')
    args=parser.parse_args()
    from openai import OpenAI, APIError
    key=read_key(args.env_file,args.key_name)
    with OpenAI(api_key=key,base_url='https://api.openai.com/v1',timeout=30,max_retries=0) as client:
        try: available={m.id for m in client.models.list()}
        except APIError as error:
            print(json.dumps({'model_check':'failed','status':getattr(error,'status_code',None)}))
            return 1
    required={args.text_model,args.vision_model,args.modeling_model,args.tts_model}
    print(json.dumps({'models':sorted(required),'available':sorted(required & available)}))
    if required-available: return 1
    if args.check_models: return 0
    args.data_dir.mkdir(parents=True,exist_ok=True)
    env={'OPENAI_API_KEY':key,'OPENAI_MODEL_TEXT':args.text_model,'OPENAI_MODEL_VISION':args.vision_model,
         'OPENAI_MODEL_MODELING':args.modeling_model,'OPENAI_REASONING_MODELING':args.modeling_effort,
         'OPENAI_MODEL_TTS':args.tts_model,'ASSISTANT_ORIGIN':f'http://127.0.0.1:{args.port}',
         'STUDIO_DATA_DIR':str(args.data_dir/'studio'),'TOUR_DATA_DIR':str(args.data_dir/'tours'),
         'STUDIO_GEOMETRY':'blender','STUDIO_API_CALL_LIMIT':str(args.call_limit),
         'STUDIO_USAGE_LOG':str(args.data_dir/'api-usage.jsonl')}
    from server.assistant.app import create_app
    import uvicorn
    app=create_app(db_path=args.data_dir/'assistant.sqlite',env=env)
    print(f'Local Studio: http://127.0.0.1:{args.port}/business/create')
    uvicorn.run(app,host='127.0.0.1',port=args.port,access_log=False)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
