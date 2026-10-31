"""Parse/render Mermaid locally with a QA-only npm install and Playwright.

No external renderer receives diagrams. npm/Playwright are not app dependencies.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT/'docs/Business Workflow Langgraph'


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mermaid-root', required=True, type=Path)
    parser.add_argument('--browser', required=True)
    args = parser.parse_args()
    tools = args.mermaid_root.resolve(strict=True)
    package = tools/'node_modules/mermaid/package.json'
    version = json.loads(package.read_text(encoding='utf8'))['version']
    shutil.copy2(ROOT/'web/assets/manrope-variable.ttf', tools/'manrope-variable.ttf')
    (tools/'index.html').write_text('''<!doctype html><html><head><meta charset="utf-8">
    <style>@font-face{font-family:Manrope;src:url('/manrope-variable.ttf')}body{margin:24px;background:#fff;font-family:Manrope,Arial}#output{display:inline-block}#output>svg{max-width:none!important}</style>
    </head><body><div id="output"></div></body></html>''', encoding='utf8')
    output = ROOT/'tests/ai/evidence/studio-refinement'
    output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1',0), partial(QuietHandler,directory=str(tools)))
    thread = threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    results = []
    try:
        base = f'http://127.0.0.1:{server.server_port}'
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True,executable_path=args.browser)
            try:
                page = browser.new_page(viewport={'width':1800,'height':1100})
                page.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base+'/') else route.abort())
                for label, filename in [('business','Estagent_Business_LangGraph_Flow.mmd'),
                                        ('native','Estagent_Business_LangGraph_StateGraph.mmd'),
                                        ('reference','Estagent_Business_LangGraph_Flow.reference.mmd')]:
                    page.goto(base+'/index.html')
                    rendered = page.evaluate('''async ({text,id}) => {
                      await document.fonts.load('13px Manrope');
                      const {default:mermaid}=await import('/node_modules/mermaid/dist/mermaid.esm.min.mjs');
                      mermaid.initialize({startOnLoad:false,securityLevel:'strict'});
                      const parsed=await mermaid.parse(text);
                      const {svg}=await mermaid.render(id,text);
                      document.querySelector('#output').innerHTML=svg;
                      await document.fonts.ready;
                      return {svg,type:parsed.diagramType};
                    }''',{'text':(FOLDER/filename).read_text(encoding='utf8'),'id':'diagram-'+label})
                    (output/f'diagram-{label}.svg').write_text(rendered['svg'],encoding='utf8')
                    page.locator('#output').screenshot(path=str(output/f'diagram-{label}.png'))
                    results.append({'file':filename,'parsed':True,'rendered':True,'type':rendered['type']})
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    result = {'status':'PASS','mermaid_version':version,'renderer':'localhost only','diagrams':results}
    (output/'mermaid-validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
