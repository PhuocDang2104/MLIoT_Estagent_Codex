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

Production now runs accepted clean source `fc3fdd301a30d72d3de554b7d4894a27124c08f9`,
healthy image `fc63867e0a1dadad41212f8796fe9d4e443f53d8eb22685918e47cf5766689d2`.
Main also contains subsequent evidence-only documentation; these do not require
another runtime rollout. The actual rollback baseline is279da1a (not initialbad806c),
with its own env and guide-v2 catalog. Keyless1, narration0, video export1, private
MinIO and API/storage guards1 are retained; both provider keys remain empty.
Stopped-instance SQLite/MinIO archives were created;12SQLite integrity checks passed.
No production uploads/chat/publish occurred. Actual TLS browser checks PASS for
landing, canonical Creator/legacy aliases, Viewer at1440/390/320, and recorded guide.
Root independently accepted actual390px Viewer, opening1/4,30right-arrow boundary
with zero missing-region pixels, hidden unavailable controls and zeroJS/writes.
Public manifest and8asset hashes are unchanged;6frontend source hashes match.
Full metadata is in `deploy/evidence/demo-ux-release/release.json`.

No claims of live OpenAI/vision, new speech synthesis, reconstruction or physical
iOS testing. Scene defaults are grounded text/neutral labels, not detected rooms.

## Concurrent-main guard

Before push, the ancestry guard caught new main2b6a332 (stale audio-ended guard
for the cached house guide). It was merged as c430680; no commit was discarded.
Strict web passed again. The changed guide browser passed against actual decoded
production WAVs on the then-current production frontend: natural transitions,
stale-ended rejection while playing/paused, all16views to finish at8x QA speed,
VI script, pause/resume/manual navigation, rotation/reduced-motion and no JS errors.
Evidence: `guide-before-deploy.json`; screenshots remain local.

The guard caught another concurrent commit279da1a before push. Its description/
recording separation and guide-v2 importer were preserved in mergefc3fdd3; only
appended declaration text conflicted. Strict web and targeted guide checks passed.
QA provenance correction: an attempted `/demos/house.js` override did not match
actual `/demos/static/house.js`; predeploy guide evidence is actual prior-production,
not a candidate override. Postdeploy checks use no overrides and compare exact
source hashes. Viewer smoke also changed its summary selector to a direct child
after nested source disclosure made the old selector ambiguous. No app change.
