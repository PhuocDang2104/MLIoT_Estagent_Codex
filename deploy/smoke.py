"""HTTP health/smoke without valid model requests, profile writes, or paid calls."""
import argparse
import json
import os
from http.cookies import SimpleCookie
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check(condition, message):
    if not condition:
        raise ValueError(message)


def run(args):
    base = args.base_url.rstrip('/')
    parsed = urlsplit(base)
    check(parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username
          and not parsed.password and not parsed.path and not parsed.query and not parsed.fragment,
          'base-url must be an HTTP(S) origin without credentials/path')
    opener = build_opener(NoRedirect())

    def request(path, body=None, headers=None):
        try:
            response = opener.open(Request(base + path, data=body, headers=headers or {}), timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.headers, response.read(1024 * 1024)

    status, headers, body = request('/api/assistant/state')
    check(status == 200, f'state HTTP {status}; expected 200')
    state = json.loads(body)
    check(isinstance(state, dict), 'state must be a JSON object')
    check(isinstance(state.get('profile'), dict) and isinstance(state.get('configured'), bool),
          'state does not match the existing assistant contract')
    check(headers.get('Cache-Control') == 'no-store', 'state must not be cached')
    studio_status, _, studio_body = request('/api/studio/health')
    check(studio_status == 200 and json.loads(studio_body).get('ready') is True,
          'Studio dispatcher or metadata store is unavailable')
    if not args.allow_unconfigured:
        check(state['configured'], 'backend unconfigured; no OpenAI key is loaded')
    if args.health_only:
        print('HEALTH PASS (HTTP + checkpoint read; no model/quota check)')
        return

    check(bool(args.origin), '--origin is required for full smoke')
    cookies = SimpleCookie()
    cookies.load(headers.get('Set-Cookie', ''))
    cookie = cookies.get('estagent_assistant')
    check(cookie is not None, 'state did not create its existing session cookie')
    check(cookie['httponly'] and cookie['samesite'].lower() == 'strict'
          and cookie['path'] == '/api/assistant/', 'session cookie flags/path mismatch')
    if args.origin.startswith('https://'):
        check(bool(cookie['secure']), 'HTTPS origin must set Secure cookie')
    session = {'Cookie': f'estagent_assistant={cookie.value}', 'Content-Type': 'application/json'}
    status, _, _ = request('/api/assistant/turn', b'{}', {**session, 'Origin': 'https://invalid.example'})
    check(status == 403, f'wrong-origin HTTP {status}; expected 403')
    session['Origin'] = args.origin
    status, _, _ = request('/api/assistant/turn', b'{}', session)
    check(status == 422, f'invalid turn HTTP {status}; expected 422 without model call')
    status, _, _ = request('/api/assistant/turn', b'x' * 65537, session)
    check(status == 413, f'oversized body HTTP {status}; expected 413')
    if not state['configured']:
        status, _, _ = request('/api/assistant/turn', json.dumps({
            'text': 'Local unconfigured smoke', 'request_id': 'deploy-no-key-0001',
        }).encode(), session)
        check(status == 503, f'unconfigured turn HTTP {status}; expected 503')
    if args.check_static:
        status, _, body = request('/assistant.html')
        check(status == 200 and b'assistant.js' in body, 'assistant HTML unavailable')
    print('SMOKE PASS: state/cookie, wrong origin, invalid turn, body limit'
          + (', unconfigured=503' if not state['configured'] else '')
          + ('; static HTML' if args.check_static else '')
          + '; no valid model request or profile mutation sent')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:5180')
    parser.add_argument('--origin')
    parser.add_argument('--health-only', action='store_true')
    parser.add_argument('--check-static', action='store_true')
    parser.add_argument('--allow-unconfigured', action='store_true',
                        default=os.environ.get('ESTAGENT_KEYLESS_PREVIEW', '0') == '1',
                        help='local diagnostics or explicitly configured keyless preview')
    try:
        run(parser.parse_args())
    except (ValueError, URLError, TimeoutError, OSError) as error:
        # Never print response bodies, session cookies, or network URLs with credentials.
        print(f'SMOKE FAIL: {error if isinstance(error, ValueError) else type(error).__name__}')
        raise SystemExit(1)
