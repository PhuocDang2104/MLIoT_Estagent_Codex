# Creator / Business AI Generation Studio

Date: 2026-10-31. Integration base: `533c3be` (fetched during implementation).
The user authorizes implementation, testing and Git integration. This card owns
`server/creator/`, additive changes to `server/assistant/app.py`, `web/studio*`,
links in `web/creator.html` and `web/index.html`, web build/lint, new Studio tests,
`fixtures/studio-*`, `scripts/gate.sh`, `.env.example`, deploy packaging/config,
this document and additive notes in CONTRACTS/DECLARATION/DEPLOYMENT.

The remote gained Creator/Viewer integration while the first implementation was
being tested. This version is built on that remote, keeps its `/api/tours/*`,
checkpoint Manifest schema, creator/viewer pages, panorama renderer, deployment
keyless-preview controls and VM/DuckDNS direction. No existing drafts or
published snapshots are migrated or overwritten. Generation Studio has its own
versioned package and private storage; it is an additional creation workflow.

Open `/business/create` or follow AI Generation Studio from Creator. The app
factory serves the route; static VM Caddy rewrites it to `studio.html`.
`studio-tour.html?id=...` is the read-only output of this workflow. Existing
`creator.html` and `viewer.html` continue to use their existing contract.

## API and persistence

Private prefix `/api/studio`: GET session; POST/GET projects; POST/GET/DELETE
project assets; POST project generations; GET generation and SSE events;
POST generation review/retry/publish. IDs are random UUID hex. JSON operations
have request_id deduplication; same ID with different payload returns 409.
POST/DELETE require exact ASSISTANT_ORIGIN; JSON body <=64 KB, binary <=20 MB.
Cookie `estagent_studio` is HttpOnly, SameSite strict, scoped to `/api/studio/`.
Asset access and generation mutation are bound to the owning cookie session.

New public prefix `/api/studio-tours/{id}`: read published package, read only
assets in that snapshot, POST questions. Viewer cookie and request history are
separate from Creator. OpenAI receives only approved published context and the
question/current checkpoint. It cannot edit metadata or publish; navigation IDs
are validated. No legacy `/api/tours/*` route or schema is changed.

STUDIO_DATA_DIR defaults to `studio` beside ASSISTANT_DB; Compose uses
`/data/studio`. creator.sqlite stores metadata/assets/events/snapshots/requests;
graph.sqlite stores LangGraph checkpoints. Run one API process and one execution
worker. Back up these DBs together with assistant and existing tour storage.
This implements local/VM SQLite, not Redis, Supabase or multi-process locking.

## Workflow

understand -> scene (one checkpoint per image) -> spatial -> spatial review
interrupt -> build_model -> mapping -> semantic -> navigation -> narration ->
final review interrupt -> voice (one checkpoint per segment) -> assembly.

Input: name/description, 1-12 images, optional floorplan and licensed WAV music,
locale and voice. Total input <=80 MB. Images are verified with the existing
Pillow dependency; SHA-256 prevents duplicate uploads. Images remain ordinary
photos unless Business explicitly confirms equirectangular 360x180 input and
the dimensions are consistent. Aspect ratio alone never proves panorama.

Review accepts room labels/yaw and explicit two-way links with yaw/pitch. All
checkpoints must be reachable. The LLM never invents measured room dimensions or
adjacency. Navigation builds validated hotspots and a connected itinerary.
Uncertain layout remains marked estimated; uploaded floorplan is shown as source.

Trusted adapter seam: `create_app(creator_worker=adapter)`; implement
`build(project, rooms, connections, assets) -> {glb: bytes, anchors: {...}}`.
Each checkpoint anchor has position [x,y,z] and matching room_id. Resolve private
asset IDs through backend storage; use generation_id as external job idempotency
key. Geometry/container/mapping validation occurs before downstream work.
With no worker, the graph interrupts as waiting_integration. It cannot publish
or be bypassed by a browser final-approval request. Restart with an adapter and
retry the same generation; completed vision and spatial review remain saved.
No Blender Python or shell supplied by a model is executed here.

Final review can edit per-room narration before TTS. Completed draft is separate
from publish. Publish requires approval, existing geometry/audio and credited
music; snapshots are immutable. The share page provides confirmed panorama/photo
views, linked checkpoints, introduction/room audio, gain controls, ducking,
pause/subtitles and read-only OpenAI Q&A. Asking a question pauses narration and
does not auto-resume. GLB is downloadable; a full browser GLB renderer is pending.

## OpenAI / limits

Development mode: fixture, USD 0 / zero live OpenAI or Blender calls. Runtime
uses only OPENAI_API_KEY on the backend. OPENAI_MODEL_TEXT defaults to the
existing gpt-6.1-sol; VISION defaults to text; TTS defaults to gpt-4o-mini-tts.
There is no provider/model fallback. Approved host: api.openai.com; only this
project's description/images/scripts and published Viewer context are sent.
No tools, tracing, secret logs or public API keys are introduced.

One generation executing, queue <=8, timeout 30s/call, SDK retries zero. At most
14 structured generation calls (brief, <=12 images, narration) and <=13 TTS
segments; max structured output 2400 tokens. Explicit retry capped at 3 execution
attempts; no automatic paid retry after restart. A call in flight during process
death is not exactly-once; completed checkpointed calls are retained. Viewer:
800 output tokens, 20 questions/session/tour, one outstanding question. Cookie
limits are not account authentication or a service-wide billing ceiling.

Official references: https://developers.openai.com/api/docs/guides/structured-outputs
and https://developers.openai.com/api/reference/resources/audio/subresources/speech/methods/create.

## Run / verification

Use `bash scripts/dev.sh` from the integrated repository, or uv run with the
pinned requirements and `python -m uvicorn server.assistant.app:app` on port 5180.
Do not copy another person's env. No-key mode permits storing/reloading input and
disables paid generation honestly. Add --env-file only for your private config.

Acceptance: strict web/AI gates, existing tour regression tests, real HTTP ->
LangGraph -> SQLite, three browser modes (worker absent, synthetic worker/full
publish, actual no-key app), screenshots and attribution. Studio schema is
`fixtures/studio-tour.schema.json`; the original tour schema stays unchanged.
Evidence is under `tests/ai/evidence/creator/`; all property/media are synthetic.
Global strict gate still reports the independent missing core lane. Per AGENTS,
main stays unmerged while that gate is red. Docker daemon is unavailable here;
no Docker/TLS/production rollout or OpenAI live verification is claimed.

No new runtime dependency. Reused pinned SDKs, Pillow 11.3.0, Manrope/branding;
new modules/UI written with Codex. Test PNG/GLB triangle/WAV silence are generated
by stdlib, not reconstructed property or actual speech. User reference PNG was
viewed locally only. H0 unknown; no claim of build during competition hours.
