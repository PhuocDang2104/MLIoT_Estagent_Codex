# Demo Viewer acceptance

Owner: Viewer lane, branch `web/demo-viewer`. Base `d73ba6a`; synchronized with
`origin/main` at `bad806c` to retain generated narration and audio-language selection.
No publish/deploy or production-data writes. Existing backend/schema unchanged.

- `UV_OFFLINE=1 bash scripts/gate.sh web --strict`: PASS lint, tests, build, schema.
- `node --test web/tests/viewer-camera.test.js`: PASS. Independent cylinder-ray
  projection checks 4,320 camera combinations (25 rays each), including 30–360°
  coverage, portrait/landscape viewports, pitch, yaw and zoom extremes.
- `playwright-cli -s=demo-viewer --raw run-code --filename=tests/demo-ux/viewer-browser.js`:
  PASS against static source served on `127.0.0.1:5277`.
  Mocked API + synthetic PNG/WAV; real Chromium, WebGL pixels and media playback.
  Desktop 1440px, mobile390/320: full viewport photo, no overflow, opening scene
  first, zero uncaptured dark pixels after arrows/drag/wheel/resize.
  Keyless chat/empty audio hidden; recorded Listen CTA plays; audio-language
  selector remains accessible when current language has no recording. Generated
  source labels and transcript language preserved. Locale switch/chat pause without
  automatic resume; Listen state clears at end. Questions/history/suggestions and
  localized provider failure verified; chat scroll stays inside its conversation without
  moving the immersive viewport; no JavaScript exceptions.

Evidence: `viewer-gate.log`, `viewer-browser.log`, `viewer-photo-*.png`,
`viewer-panorama-edge.png`, `viewer-chat.png`, `viewer-audio-*.png`,
`viewer-sources-390.png`. Images are synthetic blocks, not uploaded property data.

Reproduce: serve `web/` on local port5277; open named playwright session first;
run browser script above. Root performs independent integrated backend acceptance.
Old `tests/immersive/audio-browser.js` expects visible keyless chat and must be
updated by integration to reflect the newly requested hidden state.

Declaration: adapted repository Viewer/panorama source; no external dependency,
asset or paid API call. New bounds/UI/tests assisted by Codex. H0 remains unverified.
Content stays in the creator's language; interface switching does not translate it.
Conversation history here persists in the current page; no new history API/storage.
