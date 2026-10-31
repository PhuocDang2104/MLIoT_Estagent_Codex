#!/usr/bin/env bash
# Gate của từng lane. Phần nào chưa có code thì SKIP; --strict (bật từ H1) coi SKIP là fail.
# Dùng: scripts/gate.sh <web|core|ai|all> [--strict]
set -uo pipefail

lane="${1:?dùng: scripts/gate.sh <web|core|ai|all> [--strict]}"; strict="${2:-}"
cd "$(git rev-parse --show-toplevel)"
fail=0; skip=0

run()  { local t; t="$(mktemp)"; echo "▶ $1"; shift; if "$@" >"$t" 2>&1; then echo "  ok"; else echo "  FAIL"; tail -20 "$t"; fail=1; fi; rm -f "$t"; }
skip() { echo "▶ $1"; echo "  SKIP ($2)"; skip=1; }
py()   { if command -v uv >/dev/null; then uv run --quiet --with pytest --with jsonschema python "$@"; else python3 "$@"; fi; }

contract() {
  if [ ! -f fixtures/tour.schema.json ]; then skip contract "chưa có fixtures/tour.schema.json"; return; fi
  run "contract tour.json" py - <<'EOF'
import json, glob, jsonschema
schema = json.load(open("fixtures/tour.schema.json", encoding="utf-8"))
files = glob.glob("fixtures/**/tour.json", recursive=True) + glob.glob("projects/*/tour.json")
assert files, "không có tour.json nào để kiểm"
for f in files:
    jsonschema.validate(json.load(open(f, encoding="utf-8")), schema)
print(len(files), "tour.json hợp lệ")
from pathlib import Path
studio_schema = Path('fixtures/studio-tour.schema.json')
if studio_schema.exists():
    schema = json.loads(studio_schema.read_text(encoding='utf-8'))
    studio_files = glob.glob('fixtures/**/studio-tour.json', recursive=True)
    assert studio_files, 'không có Studio fixture để kiểm'
    for f in studio_files:
        jsonschema.validate(json.loads(Path(f).read_text(encoding='utf-8')), schema)
    print(len(studio_files), 'Studio packages hợp lệ')
EOF
}

gate_web() {
  if [ ! -f web/package.json ]; then skip web "chưa có web/package.json"; return; fi
  for s in lint test build; do
    grep -q "\"$s\"" web/package.json && run "web $s" npm --prefix web run --silent "$s"
  done
}

gate_py() {  # $1 = core|ai, $2.. = thư mục code
  local l="$1"; shift
  local dirs=(); for d in "$@"; do [ -d "$d" ] && dirs+=("$d"); done
  if [ ${#dirs[@]} -eq 0 ]; then skip "$l" "chưa có code"; return; fi
  run "$l compile" python3 -m compileall -q "${dirs[@]}"
  if [ -d "tests/$l" ]; then
    if [ "$l" = ai ] && [ -f server/assistant/requirements.txt ] && command -v uv >/dev/null; then
      run "$l pytest" uv run --quiet --python 3.13 --with pytest --with jsonschema --with-requirements server/assistant/requirements.txt python -m pytest -q "tests/$l"
    else
      run "$l pytest" py -m pytest -q "tests/$l"
    fi
  else skip "$l tests" "chưa có tests/$l"; fi
}

case "$lane" in
  web)  gate_web; contract ;;
  core) gate_py core pipelines/core ;;
  ai)   gate_py ai server pipelines/ai; contract ;;
  all)  gate_web; gate_py core pipelines/core; gate_py ai server pipelines/ai; contract ;;
  *)    echo "lane không hợp lệ: $lane" >&2; exit 2 ;;
esac

[ "$strict" = "--strict" ] && [ $skip -eq 1 ] && { echo "GATE FAIL (strict: còn SKIP)"; exit 1; }
[ $fail -eq 0 ] && echo "GATE OK ($lane)" || { echo "GATE FAIL ($lane)"; exit 1; }
