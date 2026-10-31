"""Read-only production visual audit with local frontend route overrides; no uploads/provider."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[2]
Path('/private/tmp/estagent-immersive-evidence').mkdir(exist_ok=True)
source=(ROOT/'tests/immersive/audit-production.js').read_text().replace('__ROOT__',str(ROOT))
result=subprocess.run(['playwright-cli','-s=immersive','run-code',source],cwd=ROOT,text=True,capture_output=True,timeout=150)
(ROOT/'tests/immersive/evidence/visual-browser.log').write_text(result.stdout+result.stderr)
if result.returncode or '### Error' in result.stdout or '"pass":true' not in result.stdout:raise SystemExit(result.stdout+result.stderr)
print('PASS visual audit; tests/immersive/evidence/visual-browser.log')
