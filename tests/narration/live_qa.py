"""Explicitly authorized two-call QA only. Never called by pytest/startup."""
import io
import json
import os
from pathlib import Path
import tempfile
import wave
from dotenv import dotenv_values
from openai import OpenAI, APIStatusError
from server.narration.provider import OpenAISpeech


def main():
    # Do not export the environment: chatbot/Realtime must remain keyless.
    values=dotenv_values('/Users/anhoaithai/Documents/AHT/1. PROJECTS/CodexHackathon/.env.local')
    key=values.get('OPENAI_TTS_API_KEY') or values.get('OPENAI_API_KEY')
    if not key:print('BLOCKED: OPENAI_TTS_API_KEY / OPENAI_API_KEY missing');return 1
    model=values.get('OPENAI_MODEL_TTS') or 'gpt-4o-mini-tts'
    voice='coral'  # existing Creator ProjectCreate default, no clone
    folder=Path(tempfile.mkdtemp(prefix='tour-tts-live-',dir='/private/tmp'));folder.chmod(0o700)
    client=OpenAI(api_key=key,max_retries=0,timeout=30)
    provider=OpenAISpeech(client,model);results=[]
    samples={'en':'Welcome to the tour. Choose a stop to explore the space.',
             'vi':'Chào mừng bạn đến với tour. Hãy chọn một điểm xem để khám phá không gian.'}
    try:
        for locale,text in samples.items():
            assert len(text)<=300
            try:
                body=provider.generate(text,locale,voice)
                target=folder/f'{locale}.wav';target.write_bytes(body);target.chmod(0o600)
                with wave.open(io.BytesIO(body)) as wav:
                    result={'locale':locale,'characters':len(text),'bytes':len(body),'rate':wav.getframerate(),
                            'channels':wav.getnchannels(),'bits':wav.getsampwidth()*8,'duration_seconds':wav.getnframes()/wav.getframerate()}
                assert result['duration_seconds']>0 and result['bits']==16 and result['rate']==24000
                results.append(result)
            except APIStatusError as error:results.append({'locale':locale,'error':'provider_http','status':error.status_code})
            except Exception as error:results.append({'locale':locale,'error':type(error).__name__})
    finally:client.close()
    report={'model':model,'voice':voice,'max_retries':0,'timeout_seconds':30,'samples':results,'private_output':str(folder)}
    target=folder/'verification.json';target.write_text(json.dumps(report,ensure_ascii=False,indent=2));target.chmod(0o600)
    print(json.dumps(report,ensure_ascii=False))
    return int(any('error' in row for row in results))
if __name__=='__main__':raise SystemExit(main())
