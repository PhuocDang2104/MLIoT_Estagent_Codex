# Demo UX integration — 2026-10-31

Integration branch `integration/demo-ux`; root remains reviewer/coordinator.
Base advanced from d73ba6a to bad806c before lane integration. Backend2a84d3e
was cherry-picked as97537fb; Viewer20c8974 and Creator269f2e2 were merged with
full histories. The sole product conflict was appended CSS; both scoped blocks
were retained. Existing TTS, native export and private sample-home functionality
remain included. No schema, storage migration, dependency or paid API changes.

## Delivered

- Ordinary-photo and panorama tours share the immersive viewport. Camera bounds
  include the full visible ray extent; the opening scene displays first.
- Empty audio and unavailable AI controls disappear; real narration gets Listen.
  Sources collapse into an expandable disclosure. Chat UI keeps page-local history.
- One creation entry at `/business/create`, with old Creator links and existing
  Studio project workspaces preserved. Description/title seed the draft; keyless
  create no longer sends a failing chat request. Source-language selection stays
  independent of UI labels. Audio uploads fold into Advanced, chat column sticks
  on desktop, attachment count and Publish explanation are explicit.
- Shared API helper localizes legacy bilingual errors, hides operator config,
  and retains field validation detail. EN/VI UI does not translate source prose.

## Verification

`deploy/evidence/demo-ux-release/`: web/AI strict PASS; core strict remains the
known missing-code SKIP. Extra narration/export/demo API tests:15PASS. Node error
helper tests:3PASS. Viewer ray tests cover4320camera combinations; lane browser
uses mocked API plus real WebGL/media, explicitly labeled as such.

Independent integrated browser uses real localhost HTTP/SQLite and three generated
PNGs: description → create → save → private preview → review/publish → Viewer,
1440/390/320, sourceVI retained after UIEN, opening1/3, hidden unavailable controls,
immutable snapshot after later edit, preserved Studio project route and aliases,
zero JS errors. Actual WAV/browser/restart regression passes decode/durations,
mute/gain/ducking, seek, rapid navigation, missing language/scene and load failure.
Configured-chat pause/no-autoresume remains in Viewer lane browser regression.
The updated original narration browser harness also passes real SDK-fixture WAV
generation→preview→attach EN/VI and hidden/no-generation keyless controls.
Root independent GET-only QA additionally used the actual four production
panoramas with integrated local frontend: 48 boundary checks at 1440/390/320,
maximum missing-region shader-color fraction0.000004223 (at most3pixels),
opening1/4, fullscreen stage, hidden unavailable controls and zero JS errors.
Real-media screenshots remain under `/private/tmp/estagent-demo-ux-review/`.
Screenshots from synthetic integration are local: `/private/tmp/estagent-demo-ux-integration/`.

Harness-only repairs: isolate import-time and runtime narration data roots; avoid
`URL` global unavailable in playwright-cli sandbox; select Viewer specifically
after Export adds a second publish link. Old keyless chat503 UI expectation is
replaced by hidden/noPOST; backend503 behavior is separately covered by API tests.

## Release state

Before this release, actual production was bad806c, image a5399bf0102a08f9a3c78ec78e78b3cf419c9c983ba7a803a9b0bb20cb196443,
healthy. Runtime flags: keyless1, narration0, video export1, MinIO, API/storage
guards1. Preserve them. No production uploads/chat/publish are part of acceptance.
Public immutable manifest and8asset hashes must match the root's before baseline.
Final accepted SHA, rollout and after-hash evidence will be recorded in release.json.

No claims of live OpenAI/vision, new speech synthesis, reconstruction or physical
iOS testing. Scene defaults are grounded text/neutral labels, not detected rooms.

## Concurrent-main guard

Before push, the ancestry guard caught new main2b6a332 (stale audio-ended guard
for the cached house guide). It was merged as c430680; no commit was discarded.
Strict web passed again. The changed guide browser passed against actual decoded
production WAVs with only candidate house.js overridden: natural transitions,
stale-ended rejection while playing/paused, all16views to finish at8x QA speed,
VI script, pause/resume/manual navigation, rotation/reduced-motion and no JS errors.
Evidence: `guide-before-deploy.json`; screenshots remain local.
