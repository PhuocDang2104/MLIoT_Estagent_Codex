"""Local UI preview. Proxies public tour GETs only; never sends user input or changes production."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError
import argparse
ROOT=Path(__file__).resolve().parents[2]
class Preview(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT/'web'),**kwargs)
    def do_GET(self):
        if self.path.startswith('/api/'):
            if not self.path.startswith(('/api/tours/session','/api/tours/published','/api/tours/assets','/api/tours/audio-assets')):
                self.send_error(403,'Public read-only preview');return
            try:
                with urlopen('https://estagent.duckdns.org'+self.path,timeout=20) as r:
                    data=r.read();self.send_response(r.status);self.send_header('Content-Type',r.headers.get('Content-Type','application/octet-stream'));self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
            except HTTPError as e:self.send_error(e.code,'Public preview request failed')
            except OSError:self.send_error(502,'Public preview unavailable')
        else:super().do_GET()
    def log_message(self,*args):pass
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=5188);args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Preview)
    print(f'PREVIEW_READY http://127.0.0.1:{args.port}/viewer.html?tour=f9c9100bf6effa0f141594dd972bed6d',flush=True)
    server.serve_forever()
