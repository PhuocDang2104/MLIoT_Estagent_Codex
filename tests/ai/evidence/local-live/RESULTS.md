# Local live Studio evaluation — 2026-10-31

Status: PASS for the scoped end-to-end local evaluation. No production deployment.
Implementation branch: `ai/house-modeling-agent`; base `b504dfe`;
initial integration preserved as `863ae2b`, streamed progress added in `58cadad`.

## Real input and outcome

- Three original ZInD house 000 panoramas: captures 12, 7 and 5, covering the
  connected kitchen/dining/living/hallway space. The supplied floorplan reference
  was derived from the existing source metadata, not estimated by a model.
- Final plan retained the source 24-vertex room outline, 2.359 m wall height and
  three camera poses. Eighteen source-observed fixtures; no invented furniture
  in the empty dining/living areas. Source images were reviewed before approval.
- Astra High produced the structured plan. A user-requested revision streamed
  2,414 characters of public reasoning summary and an unverified partial plan
  preview. The UI shows model, effort, elapsed time and counts. Raw private
  reasoning/encrypted events are not exposed. Only the completed validated plan
  is eligible for approval and Blender execution.
- Real Blender 5.2.3 CLI produced `house.glb` (1,422,364 bytes) and `house.blend`
  (302,485 bytes). Three.js loads the GLB and navigates to panoramas. One central
  dollhouse checkpoint is visible; all three captures remain reachable.
- Four real OpenAI WAV clips: 13.25, 15.95, 11.30 and 10.35 seconds (50.85 total).
  Each decoded successfully with nonzero PCM energy; hashes are in
  `live-result.json`. The 75-second Dream Culture excerpt plays with narration
  ducking and visible CC BY 4.0 attribution.
- The creator approved edited introduction/room narration, published an immutable
  snapshot, and the combined library lists it. A real Sol viewer question about
  kitchen features returned grounded text without changing the tour.

## Verification

`bash scripts/gate.sh all --strict`: PASS, no skips. See `gate-all.log`.
`scripts/check_live_studio.py published`: PASS with actual GLB, orbit/zoom,
central checkpoint, panorama switching, music/narration play/end/pause, music
credit, live Q&A and 320 px layout. No browser page errors. See
`browser-result.json`. A non-finite duration observed before audio metadata loaded
is represented as JSON null; subsequent playback had a finite duration.

Synthetic streaming evidence (`streaming-browser.json`, `streaming-fixture.png`,
`streaming-mobile-fixture.png`) separately checks event rendering, reload/replay,
mobile layout and owner privacy. It is not evidence of model quality. Real UI
screenshots and source images remain in ignored local storage, not Git.

## Recovered failures

1. The initial Astra request exceeded 300 seconds. Planning now allows 600 seconds;
   retry preserved successful brief/observation steps. One subsequent planning
   revision was explicitly requested to verify streaming and refine clearances.
2. The provider returned PCM WAV with unknown-length streaming size fields. The
   provider adapter now finalizes those fields before strict validation; ordinary
   truncated uploads remain rejected. The unfinished voice step was retried
   without repeating paid planning/observations.
3. Generated introductory copy incorrectly said panoramas were absent. Future
   prompts distinguish text intake from image observation. Final review now
   allows editing the introduction, and the published text was corrected before
   generating its narration. Obsolete failure cards disappear after retry.

## Budget and limits

Recorded Studio ledger: 14 API attempts, 13 successful responses, one timeout.
Successful text/vision usage estimates USD 1.6675 using the official model prices
checked during the run. This excludes TTS and any charge for the timed-out
request; binary WAV speech responses did not include token usage. It is not an
account billing total or a statement of the team's remaining USD 400 credits.
The launcher retains a 40-attempt cap across restarts; this is not a dollar cap.

Model defaults: `gpt-6-astra` high for geometry planning, `gpt-6.1-terra` for
observations, `gpt-6.1-sol` for brief/script/Q&A, `gpt-4o-mini-tts` for speech.
External credentials remain outside the repository and browser.

This is a connected open-plan subset, not a complete house or neural PanSplat
reconstruction. Fixture/opening dimensions are approximate. Materials are
authored procedural surfaces. One floor material per logical space means the
living carpet transition is not modeled. Some appliances use explicitly labeled
metal cabinet proxies; small fixtures, shutters and some interior wall returns
are omitted by the current scene vocabulary. Reference-image realism is not
claimed.

## Local handoff

- App: http://127.0.0.1:5180/
- Studio: http://127.0.0.1:5180/business/create
- Library: http://127.0.0.1:5180/viewer.html
- Published demo: http://127.0.0.1:5180/studio-tour.html?id=a1cad360382145c9a5e043196ef9a6ae
- Private runtime/artifacts: `projects/local-live/work/`; geometry is under
  `studio/geometry/`. This folder is ignored and must not be committed. The demo
  depends on that local storage; another clone must prepare inputs and run its
  own generation. Follow `docs/LOCAL-LIVE-RUN.md` for startup.
- Local server is left running on loopback port 5180. Browser QA session cookies
  are private; the published demo/library need no draft ownership cookie.

Source/asset attribution and AI-assisted implementation are recorded in
`docs/DECLARATION.md` and `web/assets/music/CREDITS.md`. Competition H0 remains
unconfirmed; no claim is made that all work was authored during contest hours.
