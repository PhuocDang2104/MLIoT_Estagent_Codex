#!/usr/bin/env bash
# One origin; no env files loaded automatically and no provider calls on startup.
set -euo pipefail
cd "$(dirname "$0")/.."
port="${ESTAGENT_PORT:-5180}"
export ASSISTANT_ORIGIN="${ASSISTANT_ORIGIN:-http://127.0.0.1:$port}"
exec uv run --python 3.13 --with-requirements server/assistant/requirements.txt \
  python -m uvicorn server.assistant.app:app --host 127.0.0.1 --port "$port"
