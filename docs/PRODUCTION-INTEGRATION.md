# Production integration task — 2026-10-31

User authority: pull main into a separate folder, audit all remote branches, merge
missing work, make a working main and build/deploy to the existing VNPT VM. Ask
only for important product/architecture conflicts. This explicitly authorizes
cross-lane integration, ordinary main pushes and the Estagent rollout.

Separate checkout: `production_main`. Starting main: `662d2b9`.
Remote branch audit: `ai/studio-runtime-production`, `web/creator-studio-integrated`
and `integration/wave2-release` are ancestors of main. Only
`ai/house-modeling-agent` at `45fa429` is missing (four commits).

Preserve current main's durable queue, edit proposals, API/storage limits, private
MinIO, FFmpeg exports, cached house/bilingual guide and fullscreen landing/viewer.
Integrate Astra High streaming, the scene-planning skill, local Blender,
Three.js/checkpoints, licensed placeholder music and Studio library cards.
Explicit HTTP worker configuration retains precedence; no automatic worker swap.

User decision: AI/Blender Studio is the default `/business/create`. The existing
photo editor remains available at `/business/photos`; `/creator.html` retains
photo draft links and normalizes to that route. The library includes all three
tour types. Existing published manifests and cached demo data remain unchanged.

OpenAI: official endpoints, user's external project key remains backend-only.
Defaults Astra High / Terra / Sol / gpt-4o-mini-tts. Preserve live API admission
limits and add a persistent 40-call Studio provider cap for the initial rollout;
an operator can raise it without resetting usage. This is not a USD budget cap.
Shared account allowance is USD 400; synthetic regression tests spend nothing.
Use a bounded live deployment check only after local/container verification.

Paths: integration requires root config, `server/`, `pipelines/core/`, `web/`,
`tests/`, `scripts/`, `deploy/`, `fixtures/`, `docs/` and release evidence.
Existing dependencies retained; production image adds optional Debian Blender
alongside FFmpeg. Verify actual GLB output on the deployed Blender version.
Debian's Blender 3.4.1 glTF exporter needs `python3-numpy` explicitly when using
`--no-install-recommends`; Linux acceptance exercises actual GLB export.

Added user scope: import the premade Seoul ZIP as a separate read-only library
sample with source panoramas/floorplan and original furniture. New optional
SEOUL_CATALOG_PATH, viewer and vendored MIT meshopt decoder; preparation uses
glTF Transform 4.5.0 outside app dependencies. See SEOUL-SAMPLE.md. No change to
generated-tour contracts or the existing pinned ZInD catalog.

Acceptance: strict all gate with no skips; synthetic end-to-end Studio and legacy
photo routes; real container Blender; unchanged old public tours/demo hashes;
private backup before cutover; healthy Docker/HTTPS; live progress/Three.js and
audio behavior; recorded source/image hashes and working rollback instructions.
Build from a clean accepted SHA. Preserve old releases, volumes and MinIO objects.
Do not alter unrelated VM services. Recheck remote main and running image before
push/cutover to avoid overwriting concurrent teammate changes.

Completed: deployed `ee6da34`, healthy public HTTPS and Seoul browser checks.
Full results, precise verification limits, private backup and rollback details:
`STUDIO-SEOUL-RELEASE.md`. Evidence: `deploy/evidence/studio-seoul/`.

Follow-up upload incident: the global six-upload/minute cap rejected a normal
eight-panorama batch, and manual retry resent already completed files. Correct
the non-AI upload burst to 24/minute (same window, concurrency one, ledger retained),
retain successful file progress in the current submission, and honor bounded
Retry-After waits for upload 429 responses. No AI/narration caps or schema changes.
Acceptance: real HTTP upload retry/browser regression, admission-limit tests,
web gate and guarded production update with existing data preserved.

Additional direct user request: Seoul only receives video/transcript exports and
generated voice, in English only. Prepare one bounded batch (eight cached TTS
attempts with a separate usage receipt), render a narrated 1080p video from the
original panoramas, and serve reviewed MP4/WAV/TXT/VTT through the pinned Seoul
catalog. No general public generation or ZInD export exception. User also requests
the landing model and sample CTA use the furnished Seoul home. Preserve shared
rotation/accessibility controls and disclose AI-generated voice. Validate codec,
duration, transcript/caption identity, Range/download headers and browser playback.

Upload follow-up completed at `e12582f`; evidence and exact retry behavior are in
`UPLOAD-RETRY-FIX.md`. No paid calls; all existing uploaded asset rows preserved.

Seoul media and landing follow-up completed on application release `5200bca`
with versioned media configuration; concurrent English/sample-input work retained.
See `SEOUL-MEDIA-RELEASE.md` and `deploy/evidence/seoul-media/` for production,
browser, media-hash and eight-call voice evidence. No global demo export exception.
