# Assistant evidence — 2026-10-31

- Actual FastAPI local server at 127.0.0.1:5180; actual no-key UI.
- Backend tests: 9 passed. Actual LangGraph/SQLite; model extraction and voice upstream mocked.
- Browser: passed text intake, optional skip/defer, confirmation, correction, failed-message preservation, microphone permission denial, transcript delivery to graph API, graph reply sent to voice, cancellation and microphone release. WebRTC and successful API responses mocked. 320px/390px no horizontal overflow; desktop screenshot 1440px. No JS page errors. One intentionally injected HTTP 502 logged by browser.
- Web strict gate: lint/test/build passed; contract SKIP → strict FAIL (missing fixtures/tour.schema.json).
- AI strict gate: compile/pytest passed with isolated uv + assistant requirements; same missing contract fixture → strict FAIL.
- No live OpenAI request or paid Apify run. No production deployment validated.

Reproduce:
```bash
python3 -m pytest tests/ai/test_assistant.py -q
python3 -m uvicorn server.assistant.app:app --host 127.0.0.1 --port 5180
playwright-cli -s=assistant open http://127.0.0.1:5180/assistant.html
playwright-cli -s=assistant run-code --filename=web/evidence/assistant-smoke.js
bash scripts/gate.sh web --strict
```
