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

Acceptance: strict all gate with no skips; synthetic end-to-end Studio and legacy
photo routes; real container Blender; unchanged old public tours/demo hashes;
private backup before cutover; healthy Docker/HTTPS; live progress/Three.js and
audio behavior; recorded source/image hashes and working rollback instructions.
Build from a clean accepted SHA. Preserve old releases, volumes and MinIO objects.
Do not alter unrelated VM services. Recheck remote main and running image before
push/cutover to avoid overwriting concurrent teammate changes.
