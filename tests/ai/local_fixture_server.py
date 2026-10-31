"""TEST ONLY. Real HTTP/LangGraph/SQLite; a finite model fixture, never OpenAI.

Launched by run_local_browser.py, without .env.local or inherited provider keys.
Unknown text fails explicitly; this is not a natural-language model or demo mode.
"""
import argparse
import os

import uvicorn

from server.assistant.app import create_app
from server.assistant.graph import Extraction, LABELS


def fixture_extract(state):
    cases = {
        'Căn hộ ở Quận 7, TP.HCM, diện tích 85 m², có 2 phòng ngủ.':
            ('answer', {'address': 'Quận 7, TP.HCM', 'area': 85, 'bedrooms': 2}),
        'Để tất cả các mục tùy chọn còn lại sau.': ('skip_all', {}),
        'Tôi xác nhận các thông tin trong hồ sơ đã đúng.': ('confirm', {}),
        'Sửa diện tích thành 90 m².': ('answer', {'area': 90}),
    }
    if state['text'] not in cases:
        raise ValueError('Text not in the finite model fixture')
    intent, patch = cases[state['text']]
    return Extraction.model_validate({
        'intent': intent, 'patch': {k: patch.get(k) for k in LABELS},
        'clear_fields': [], 'clarification': None,
    })


class ReadyServer(uvicorn.Server):
    async def startup(self, sockets=None):
        await super().startup(sockets)
        if self.started:
            print('LOCAL_FIXTURE_READY', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--mode', choices=['fixture', 'missing-key'], required=True)
    args = parser.parse_args()
    # This is an isolated test process. No tracing or provider keys are inherited.
    assert not any(k.startswith(('OPENAI_', 'LANGSMITH_', 'LANGCHAIN_')) for k in os.environ)
    app = create_app(
        db_path=args.db,
        extractor=fixture_extract if args.mode == 'fixture' else None,
        env={'ASSISTANT_ORIGIN': f'http://127.0.0.1:{args.port}',
             'ASSISTANT_REQUIRED_FIELDS': 'address,area,bedrooms'},
    )
    ReadyServer(uvicorn.Config(app, host='127.0.0.1', port=args.port, log_level='warning')).run()
