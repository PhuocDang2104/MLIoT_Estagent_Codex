"""One explicitly authorized Seoul-only batch. Eight TTS attempts maximum, cached.

Run from repository root with --env-file pointing to the user's external dotenv.
No key or input is printed. Output stays outside Git and outside generated tours.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import wave
from dotenv import dotenv_values
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.creator.provider import OpenAIProvider


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--env-file', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    script_path = Path(__file__).with_name('seoul_narration_en.json')
    doc = json.loads(script_path.read_text(encoding='utf-8'))
    assert doc['sample_id'] == 'seoul-apartment' and doc['locale'] == 'en' and len(doc['chapters']) == 8
    args.output.mkdir(parents=True, exist_ok=True)
    key = dotenv_values(args.env_file).get('openAIKey')
    if not key:
        raise ValueError('External openAIKey is missing')
    provider = OpenAIProvider(OpenAI(api_key=key, max_retries=0), {
        'OPENAI_MODEL_TTS': 'gpt-4o-mini-tts', 'STUDIO_API_CALL_LIMIT': '8',
        'STUDIO_USAGE_LOG': str(args.output/'provider-usage.jsonl')})
    results = []
    for chapter in doc['chapters']:
        digest = hashlib.sha256((chapter['text']+'|alloy|gpt-4o-mini-tts').encode()).hexdigest()
        output = args.output/(chapter['capture_id']+'.wav')
        receipt = output.with_suffix('.json')
        if receipt.exists():
            cached = json.loads(receipt.read_text())
            assert cached['input_sha256'] == digest and hashlib.sha256(output.read_bytes()).hexdigest() == cached['audio_sha256']
        else:
            audio = provider.speech({'voice': 'alloy'}, chapter['text'])
            output.write_bytes(audio)
            receipt.write_text(json.dumps({'input_sha256': digest, 'audio_sha256': hashlib.sha256(audio).hexdigest()}))
        with wave.open(str(output), 'rb') as wav:
            duration = wav.getnframes()/wav.getframerate()
            assert 2 <= duration <= 60 and wav.getnchannels() == 1
        results.append({**chapter, 'audio': output.name, 'duration': duration})
        print('Prepared', chapter['capture_id'], round(duration, 2), 'seconds', flush=True)
    (args.output/'chapters.json').write_text(json.dumps({'locale': 'en', 'model': 'gpt-4o-mini-tts',
        'voice': 'alloy', 'script_sha256': hashlib.sha256(script_path.read_bytes()).hexdigest(),
        'chapters': results}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
