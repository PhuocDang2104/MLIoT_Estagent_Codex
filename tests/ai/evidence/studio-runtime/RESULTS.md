# Studio runtime acceptance — 2026-10-31

Integrated upstream main `5498fdc` (contextual Creator/Viewer chat) before final QA.
Runtime framework source commits: `298c933`, `bfe1560`, `2a097d5`; final refinement
also sorts navigation neighbors by the requested checkpoint preference.

- `bash scripts/gate.sh ai --strict`: PASS, **109 passed, 0 failed, 0 skipped**,
  pinned Python 3.13 requirements. Full machine-readable results: `pytest.xml`.
- `bash scripts/gate.sh web --strict`: PASS lint/test/build and both package schemas.
- `python -m tests.ai.run_studio_qa`: PASS full, waiting-worker, keyless modes;
  actual Chromium/HTTP/LangGraph/SQLite, synthetic provider/triangle GLB/silence.
  Proposal reload, explicit confirmed fork, spatial edit before geometry, final
  approval before TTS/publish, immutable parent, media playback/ducking and 320px.
  See browser-results.json and mode subdirectories; no page errors.
- Native deploy preflight at source `2a097d5`: PASS configuration guards,
  no-key/fake-key HTTP/cookies/Origin/body/static/Studio health, SQLite reopen and
  quick_check, 11 assistant tests. `native-qa.json` records actual output.
- Compose example `config --quiet`: PASS, no daemon/model call.
- Mermaid 11.12.1 local parse/render: PASS Business/native/reference; runtime has
  15 nodes, 22 declared edges. Export JSON source hash matches current graph.py.
- Separate targeted coverage: cross-process lock, atomic immediate-review wakeup,
  queued/review/crash recovery, shutdown checkpoint, async submit-once/poll,
  ownership/stale proposal/idempotency, script/audio reuse, metadata removal,
  verified navigation preference and offline DB/media backup.

`gate core --strict` still fails with baseline `SKIP (chưa có code)`: reconstruction
is outside the user-approved framework scope. Strict-all is not claimed green;
no gate was weakened and no placeholder core was added.

All API/model/media/worker input is synthetic; USD 0, no live OpenAI/Blender,
production media or SSH mutation. Docker build/volume/TLS/rollout and real model
access/geometry accuracy remain unverified. Operator runbook: docs/STUDIO-DEPLOY.md.
The runtime supports one fenced process on one local data volume, not replicas.
Windows QA retains temporary synthetic diagnostic DBs; generated OS cache files
outside the evidence paths are not staged or included in the release.
