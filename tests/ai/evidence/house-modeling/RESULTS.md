# House-modeling integration verification

Base `b504dfe` / `web/creator-studio-integrated`; implementation branch
`ai/house-modeling-agent`. Local verification on 2026-10-31.

- Strict all-lane gate PASS: web syntax/tests/build, core compile/tests, AI
  compile/tests, both published contract schemas. See `gate-all.log`.
- Python: **45 passed**, no skips. See `pytest.log`. Includes actual Blender CLI
  export/cache, timeout/failure handling, source/geometry checks, clarification
  cap, approval, migration of an old waiting generation, and all earlier tests.
- Web: **6 passed** plus browser integration assertions.
- Skill validator PASS for `server/creator/skills/house-modeling`.
- Browser PASS: actual FastAPI/LangGraph/SQLite → automatic Blender 5.2.3 LTS →
  embedded textured GLB → Three.js. Clarification/revision, estimate acceptance,
  model marker → panorama, orbit/zoom/wall visibility, final approval, publish,
  audio playback/ducking/rapid pause, read-only Q&A and 320px layout were exercised.
  No browser page errors. See `full-browser.json` and screenshots in this folder.
- API compatibility uses the real pinned OpenAI Python SDK against MockTransport;
  validates official `/v1/responses` endpoint, strict JSON schema, image payloads,
  and `/v1/audio/speech` WAV requests. No live API requests or credit usage.

The plan, solid-color source images and silence audio are explicitly synthetic.
The geometry builder and WebGL renderer are real. These checks do not establish
image interpretation accuracy, real-house reconstruction fidelity, live model
access, provider pricing, Docker runtime performance, or production deployment.

Windows gate environment: the stock `python3` name resolves to the Microsoft
Store alias, and default output encoding cannot print the gate's Vietnamese
messages. The gate itself was unchanged. For verification, `python3` was mapped
to uv-managed Python 3.13 and `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8` were set.
The initial alias/encoding failures were environmental, not hidden test failures.

Reproduce native tests:

```sh
uv run --python 3.13 --with pytest --with jsonschema \
  --with-requirements server/assistant/requirements.txt \
  python -m pytest tests/core tests/ai -q
```

Actual-Blender tests require an installed CLI (or `STUDIO_BLENDER_EXECUTABLE`).
Without it that specific acceptance test explicitly skips; a green fixture test
alone is not evidence of Blender execution. Browser QA server and runner are
`tests.ai.modeling_browser_server` (port 5191, `CREATOR_QA_DB` points to a disposable
database) and `tests.ai.run_modeling_browser`. They never load a production key.
