# P0 Pitch candidate — W6H → root W6B / deploy W6F

Ready 2026-10-31 14:41 +07, before requested 14:42 candidate cutoff.
Branch: `integration/pitch-candidate`; worktree: `.worktrees/pitch-integration`.
Code integration SHA: `0b48b9b5d77c50371c24aa30f0a33bde565d2ea0`.
Final handoff commit is the branch tip (adds only this handoff/card/evidence); resolve with `git rev-parse integration/pitch-candidate`.

## History and scope

Fetched origin first and again immediately before handoff. Latest fetched main:
`d73ba6ab920d06aff6d043c2e3818d086ad3f2b5` (ancestor of candidate).
Fast-forwarded committed W6F release HEAD `e30f6bdd5b5d133ff3b71abb9ee8e6913bd60394`.
That HEAD already integrates TTS3298792, Video0b3c935 (native85b3fb6, parent7797ef0), Pitch UXd07e869,
Demo3D/guided private intro d54d80d+2ba3404. Merged `design/product-e2e`2fa58cb retaining parents;
only missing asset documents changed. c33e843 and immersive2c57fbd are already ancestors.
No conflict, no blind ours/theirs, no duplicate cherry-pick, no backup/Claude-attribution branch merged.
No implementation correction needed after inspecting existing committed integration.
No dirty source copied. Root checkout `.env.example` and untracked user docs untouched.
No server/demos, web/demos or library viewer edits by this lane; W6F retains that lease.

## Reviewed integration points

- App installs export exact routes before generic static allowlist; route smoke verifies export.html/js/css200.
- narration-panel.js/css in static allowlist and build; #narration-panel anchor mounted with actual api,
  fresh GET draft callback, revision/id-bound refresh, explicit attachment and separate music.
- Creator dropzone and empty-draft UX retained; publish retains Viewer/share and `/export.html?tour=` link.
- Models/schema accept none/user_uploaded/openai_generated/mixed; bilingual scene+locale binding retained.
  Export selects matching published snapshot source locale only; no translation or foreign-locale fallback.
- Nested lifespan finally closes export process scope, narration, Creator, OpenAI client and SQLite.
- Private MinIO regex includes tours/exports/<hex32>.mp4 and content type video/mp4; ownership/public snapshot
  separation unchanged. Origin rejection and owner-missing404 exercised in keyless route smoke.
- Production Dockerfile is python:3.13-slim-bookworm + ffmpeg=7:5.1.9-0+deb12u1, consistent with QA candidate.
  server/exports and server/narration copied; release package includes modules/new web files.
  Compose VIDEO_EXPORT_RENDERER=ffmpeg; no Node/Chrome/HF production requirement. Single renderer flock/job,
  bounded queue and caps remain. App caps1CPU/1GiB/pids128 retained; native QA cgroup used pids64.
- NARRATION_ENABLED/VIDEO_EXPORT_ENABLED defaults remain0; budgets require operator env. No global Realtime enabled.

## Exact acceptance

All commands run from candidate, using fixtures/synthetic media only:

1. `bash scripts/gate.sh web --strict` → PASS lint/test/build + schema. `docs/evidence/pitch-integration/web-strict.log`.
2. `bash scripts/gate.sh ai --strict` → PASS compile/pytest + schema. `docs/evidence/pitch-integration/ai-strict.log`.
3. `ASSISTANT_DB=/private/tmp/pitch-native-isolated/state.sqlite VIDEO_EXPORT_RENDERER=ffmpeg QA_OUTPUT_DIR=/private/tmp/pitch-integration-native-1440 uv run --offline --quiet --python 3.13 --with pytest --with jsonschema --with-requirements server/assistant/requirements.txt python -m pytest -q tests/narration tests/exports/test_exports.py tests/exports/test_native_config.py`
   → 12 PASS,23.07s; one existing LangChainPendingDeprecationWarning. Log `narration-native.log`; output metadata `native-exports.json` in same evidence folder.
4. Keyless FastAPI TestClient: Creator/export/narration static200, Creator anchor/import/export link, wrong Origin403,
   missing owned draft404, clean lifespan exit → PASS `routes.log`.
5. `python3 scripts/check_commit_attribution.py --all` → PASS `attribution.log`; merge hook also PASS.
6. `bash scripts/gate.sh core --strict` → FAIL solely baseline SKIP (no pipelines/core), `core-strict.log`.
   Do not describe all-strict as green.

First concurrent narration/native test collection collided with AI gate's default import-time narration worker lock.
Retried once with independent ASSISTANT_DB scratch; passed. No lock deletion, guard bypass, production data or key access.
Test-generated tracked exports evidence restored after preserving candidate-specific metadata in docs/evidence.

Linux renderer code unchanged, so reused signed-by-history evidence from85b3fb6/0b3c935:
`tests/exports/evidence/native-linux-{proof,artifacts}.json`, container1CPU/768MiB/pids64, actual H.264/AAC output,
child ru_maxrss177628KiB (not total application peak), exit0/no OOM. No redundant VM/Docker render here.
No browser rerun of unchanged UI: teammate Pitch UX and narration evidence remain the UI acceptance source;
this lane newly verifies integrated real HTTP routes and native rendering, not a production browser session.

## NEED W6F only

- Fast-forward the authorized release/main target to candidate tip if ancestry still allows; do not force if main moves.
  This lane has NOT pushed main, deployed, touched SSH/VM or read secrets.
- Build/package from the accepted clean main after normal main/origin synchronization; prepare_release intentionally
  refuses a candidate branch. Existing root .env.example dirty must remain preserved by main owner.
- Retain current safe feature flags until private MinIO MP4 + API smoke and operator TTS-only env0600/budget setup
  are accepted. Operator W6F owns enablement, seed and immutable new-snapshot provenance; never mutate public snapshot.
- Core strict baseline remains outside candidate scope. No new dependency decision or code conflict blocker.

Declaration: merges existing teammate work; this lane authored only card/handoff/evidence using Codex.
No new image/model/provider/media content, no paid API calls, H0 unknown.
