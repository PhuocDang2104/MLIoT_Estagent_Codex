# House-modeling integration task and handoff

Base: `web/creator-studio-integrated` at `b504dfe`. Working branch: `ai/house-modeling-agent`.

## Authorization and paths

The user requested whole-project integration of their existing house-modeling skill and explicitly selected **automatic Blender execution**. This card covers the necessary cross-lane additive changes: `server/creator/`, `server/assistant/app.py`, `pipelines/core/`, `tests/core/`, `tests/ai/`, `web/`, `fixtures/`, `docs/`, `.env.example`, `deploy/` and `scripts/export_studio_graph.py`. No production deployment, publishing, push or paid provider run is part of this task.

Dependencies: existing Python requirements, locally installed Blender CLI, vendored Three.js 0.180.0 (MIT). No CDN or additional Python runtime package.

## OpenAI

Use the existing backend Responses API client and configured vision model. A server-owned agent template produces typed scene data, never Python or shell code. Include uploaded panorama/photo images and the optional floorplan. At most three completed planning passes per generation (initial plus two user-requested revisions), each at most 24,000 output tokens including reasoning. Existing image observation, narration and voice budgets remain unchanged. Tests use synthetic provider responses, USD 0; actual Blender is exercised separately. No claim of live model accuracy or account access.

## API compatibility and budget

Team budget note: the user reported **USD 400 total OpenAI API credits**, shared
across the hackathon. This is not a per-generation allocation or permission to
spend the balance. Verification here costs USD 0 in OpenAI calls. Production uses
the official SDK `POST /v1/responses` (text/vision structured output) and
`POST /v1/audio/speech` (WAV), with server-side `OPENAI_API_KEY` and configurable
`OPENAI_MODEL_TEXT`, `OPENAI_MODEL_VISION`, `OPENAI_MODEL_MODELING`, `OPENAI_MODEL_TTS`. Model access must be
checked with the team's project; configured IDs alone do not prove availability.

At 12 captures: at most 17 completed structured generation calls including all
three planner passes, and 13 TTS segments after approval. Failed/in-flight calls
can still be billed and explicit retries may repeat them. Viewer Q&A has a
separate per-session cap. These are request limits, **not a USD 400 global billing
cap** across this app and the team's other work. Review actual usage before live
evaluation; no dollar estimate is hardcoded from unverified model pricing.

## Contract change

Add a private modeling plan and clarification/revision review to Studio. Keep the 12 durable nodes, with an explicit review-to-spatial revision edge. Group multiple captures into logical rooms. Geometry anchors gain optional dollhouse visibility and orientation/accuracy metadata; existing worker adapters and published v1 packages remain readable. Private input images/floorplans do not become public unless already included as approved tour panoramas. Human spatial and final approvals remain required.

The automatic builder consumes a validated, bounded scene manifest, authors materials and source-observed fixtures, exports an embedded GLB and editable Blender scene, and caches successful generation artifacts. Three.js renders the GLB in Creator and the published viewer; capture selection enters the existing panorama experience.

## Acceptance

- Existing intake, legacy tours, Studio review/retry/publish tests pass.
- Invalid geometry, unsupported evidence and unresolved layout cannot be built by approval alone.
- Missing floorplan can produce a qualified provisional plan or targeted clarification, never asserted metric truth.
- Real Blender CLI exports a textured, finite house with openings, fixtures and all capture anchors.
- Browser renders the actual GLB and transitions from a representative marker to panorama; all captures remain available.
- Strict gates, schema fixtures, skill validation, browser evidence and limitations recorded below after execution.

## Runtime and verification

Install Blender on the application host. `STUDIO_GEOMETRY=auto` (default) discovers
PATH or Windows Blender installations; use `STUDIO_GEOMETRY=blender` to require it
at startup, `STUDIO_BLENDER_EXECUTABLE` for an absolute executable path, or `off`
to retain the external-worker interruption. Timeout defaults to 180 seconds and
is clamped to 10–600 seconds. The app runs one geometry job at a time.

For Docker, the optional `--build-arg WITH_BLENDER=1` installs the distribution's
Blender. Set `ESTAGENT_MEMORY_LIMIT=4g`, `ESTAGENT_CPU_LIMIT=2.0` when qualifying
that image on the target host. This Docker variant has not been runtime-qualified;
the tested runtime is native Windows Blender 5.2.3 LTS. No deployment was changed.

The worker writes private, generation-scoped files beneath
`STUDIO_DATA_DIR/geometry/<hashed-generation>/<plan-and-builder-hash>/`:
`scene.json`, `house.blend`, embedded `house.glb`, `checkpoints.json`, completion
hash and private `blender.log`. These are recoverable editing/handoff artifacts.
Do not put this directory under the static web root. GLB is copied to the existing
owned asset store and only enters public storage through explicit publish.

Portable rerender/export: open `house.blend` in Blender, or run the checked-in
`pipelines/core/build_house.py` with Blender's `--background --factory-startup
--disable-autoexec --python-exit-code 1 --python <builder> -- <scene.json> <output-dir>`.
The directory must already exist. For the website, load GLB using GLTFLoader and
use the existing `model.anchors` / `rooms[].anchor` mapping. Units are nominal
meters, world Y up, floor top Y=0. Blender conversion is `(X,-Z,Y)`. Anchor position
is capture eye position; heading is image-center direction clockwise from world
-Z. Room `yaw` remains the panorama renderer's reviewed initial image yaw and is
not the world heading. Approximate positions are explicitly marked. Do not move
capture positions when choosing representative markers.

The builder supports one floor, bounded simple polygons, matching shared walls,
door/window/passage openings, eight authored material categories and 15 fixture
categories. It creates beveled components and exports embedded texture maps.
Fixtures require source-image citations and evidence descriptions. Their shapes
are approximate authored representations, not photogrammetry. It does not use
PanSplat, GPU rendering, projected panorama textures or automatically invent
furniture. Multi-floor reconstruction and arbitrary furniture shapes need a
future schema/builder extension. Published viewers must retain these limitations.

The graph keeps its existing 12 nodes. Spatial revisions do not repeat completed
image observations. Old saved generations without a HousePlan are redirected
through planning and human review when connected to the automatic worker.
Native Blender failures remain retryable at the existing build checkpoint;
completed exports are reused only when their content hash matches.

## Source architecture reviewed

Three flows coexist: assistant intake (fact extraction/voice), legacy tour
Creator/Viewer (photo tour and immutable publication), and the durable Studio
LangGraph. This change extends Studio. Its asset ownership, cookie/Origin checks,
SQLite checkpoints, SSE events, human reviews, narration/TTS, immutable publish,
and published-only Q&A remain the authority. The historical core contract is not
silently substituted for the newer Studio package. Release allowlists and static
build include the new worker, skill/template and self-hosted Three.js modules.

The structured output call follows the existing Responses SDK parsing seam and
[official Structured Outputs guidance](https://developers.openai.com/api/docs/guides/structured-outputs).
Typed parsing is followed by independent source-ID, footprint, shared-opening,
capture and fixture validation. Schema adherence alone is not reconstruction
accuracy; Creator approval and real input evaluation are still necessary.

## Verified result

Strict all-lane gate passed; 45 Python tests and 6 web tests passed. Local Blender
5.2.3 LTS generated an embedded textured GLB and editable scene. Browser QA passed
from upload/clarification through Blender build, Three.js checkpoint navigation,
final approval, publication and read-only Viewer/audio. Skill validation passed.
See [verification evidence](../tests/ai/evidence/house-modeling/RESULTS.md).
The provider was synthetic; OpenAI endpoint/schema compatibility used the real
SDK with mocked HTTP. No API credits were spent, no live accuracy claim is made,
and no production deployment or push was performed.

Current model defaults and separately authorized live evaluation supersede the original offline-only budget above; see `LOCAL-LIVE-RUN.md`.
