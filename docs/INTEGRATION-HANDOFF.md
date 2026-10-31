# Product integration handoff — Tatejo review required

**Vertical slice implemented and exercised locally. Overall status PARTIAL:** visual Creator→Viewer flow
works, but core reconstruction does not exist, audio assets are unavailable, and OpenAI live was not called.
This is a lane handback, not a declaration that the full product or deployment is complete.

## Ownership and Git

- Received from: Tatejo, with Thái's explicit cross-lane PRODUCT INTEGRATION authorization and later
  rental-seeker/JTBD context. Independent Claude review described old MAIN source, not this browser run.
- Cwd: `/Users/anhoaithai/Documents/AHT/1. PROJECTS/CodexHackathon/.worktrees/product-sync`.
- Branch: `integration/product-sync`; base: `da2105de1ada4ae865cd5d293553c28c219a4476`.
- Implementation commit: **`3cb92285055315868585b15db82c8c141b08b641`**. This follow-up only records the verified implementation SHA. No merge, push, deploy, auth, SSH,
  GPU, model download or sub-agent. Main checkout was not modified.
- Source files: `server/tours/{api,models}.py`, `web/{creator,viewer,tour-common,panorama}.js`,
  `web/{creator,viewer}.html`, `web/tour.css`, `server/assistant/app.py`.
- Public entry routes: `/` landing, `/creator.html`, `/viewer.html`. `experience.html` redirects to Creator.
  Existing `/api/assistant/*` stays compatible. Direct `/assistant.html` remains the legacy Vietnamese
  property-intake utility for compatibility; it is **not linked from the integrated product flow**.
  Its browser-only predecessor modules are no longer loaded by the Creator route.

## Run and inspect

```bash
bash scripts/dev.sh
```

URL: **http://127.0.0.1:5180/**, all assets/API/pages same-origin. Optional `ESTAGENT_PORT` changes the
local port; an explicitly supplied `ASSISTANT_ORIGIN` must exactly match. No env file loaded automatically.
Runtime needs uv + Python 3.13; frontend checks need Node. Keyless startup is intentional and not a mock AI.

1. Create tour → upload synthetic or authorized JPEG/PNG/WebP photos → optionally send text.
2. If no OpenAI key, chat visibly returns 503 while the saved visual draft remains editable.
3. Rename/reorder, choose opening checkpoint; ordinary photos remain gallery. Explicitly select and
   calibrate cylindrical panorama for appropriate input. Missing coverage stays blank; no inferred 360/3D.
4. Save → open private preview → check review/rights confirmation → publish → open/copy Viewer link.
5. Change draft; published snapshot must stay unchanged. Reload/restart preserves both.

No dataset is bundled. Fresh app starts with no published tour. Tests generate geometric synthetic
images in gitignored worktree runtime storage. Do not put the private PDF/demo ZIP/photos into Git.

## Persistence/config/contract

- Additive contract `checkpoint-tour-v1` in `docs/CONTRACTS.md §7`; runtime Pydantic models and generated
  JSON Schema are checked for equality. Legacy reconstruction draft remains labelled unimplemented.
- New `/api/tours/` routes: cookie session, decoded image ingestion/private assets, revisioned draft,
  text+attachment references/history, text assistant edit, review, immutable publish snapshot,
  public read/asset access, read-only Viewer Q&A/navigation.
- Exact Origin, per-session ownership, random server IDs, decode/signature checks, metadata stripping,
  thumbnail generation, body/pixel/file caps, idempotent create/publish and revision guards. Stale
  model results cannot overwrite a later user edit. Viewer model output cannot change metadata.
- New local `tours.sqlite` + normalized JPEGs next to ASSISTANT_DB, default
  `projects/assistant/work/tours/`. `TOUR_DATA_DIR` overrides; an explicitly blank path fails clearly.
  No production migration, no access to existing external DB, single worker only.
- Assistant cookie path `/api/assistant/` unchanged. Separate tour cookie `/api/tours/`, HttpOnly,
  SameSite Strict, 30 days, Secure when configured HTTPS. This is session isolation, not account auth.
- Published snapshots intentionally available to anyone able to reach this local server. No auth,
  public-production abuse controls, deletion/retention UI, storage quota beyond per-session caps, or
  distributed job queue added. Do not claim production readiness.
- New dependency `Pillow==11.3.0`: actual image decode/orientation and derivatives; installed package
  metadata declares `License-Expression: MIT-CMU`, `License-File: LICENSE`. Other pins unchanged.

## Evidence and exact commands

All evidence lives under `tests/integration/evidence/`, plus legacy compatibility evidence under
`tests/ai/evidence/`. Logs do not include cookies, keys, SDP, image bytes or user data.

| Check | Result / evidence |
|---|---|
| `npm --prefix web run lint`, `test`, `build` | PASS; 6 existing frontend unit tests, syntax checks include all new modules; in strict gate log |
| `uv run --python 3.13 --with pytest --with jsonschema --with-requirements server/assistant/requirements.txt python -m pytest tests/ai -q` | **20 passed** (11 existing assistant + 9 new tour tests); `api-tests.log`. One pre-existing LangChain deprecation warning |
| `uv run --python 3.13 --with-requirements server/assistant/requirements.txt python tests/integration/run_browser.py` | Real Chromium/HTTP/SQLite/Pillow/WebGL; `browser.log`, `server.log`; no app API route mocks |
| Browser visual flow | Upload→draft→rename/reorder/start→save→reload→private preview→review→publish→Viewer; later edit does not mutate snapshot; 320/390/1440 viewport, EN/VI navigation, reduced-motion; JS errors=0, unexpected HTTP errors=0 |
| Browser restart and assistant | Actual backend process restart; draft/images/snapshot/history survive. Finite injected provider edits name/order through real backend and answers Viewer from snapshot; explicitly **not OpenAI live** |
| Dynamic manifest | 1/4/5 scene navigation, loaded images and wrapping checked in browser; no hardcoded demo filenames/count |
| Missing key | Real Creator and Viewer HTTP 503, message retained for retry, visual draft retained. Legacy API text/voice 503 also covered |
| `python3 tests/integration/check_dev_command.py` | PASS actual `bash scripts/dev.sh` in isolated env, real origin with landing/Creator/Viewer/motion/favicon/APIs all HTTP 200; `dev-command.log` |
| `uv run --python 3.13 --with pytest --with jsonschema --with-requirements server/assistant/requirements.txt python tests/ai/run_local_browser.py` | Legacy assistant HTTP→LangGraph→SQLite flow/restart/missing-key PASS; `tests/ai/evidence/local-browser.log` |
| `bash scripts/gate.sh all --strict` | **Exit 1, baseline core SKIP only**. Web lint/test/build PASS, AI compile/tests PASS, contract PASS. `gate-strict.log`. No gate weakened |
| `python3 scripts/check_commit_attribution.py --all`, `git diff --check` | PASS; attribution log. No Claude attribution added |

Screenshots: `creator-desktop.png`, `creator-mobile-chat.png`, `creator-mobile-draft.png`,
`viewer-desktop.png`, `viewer-mobile-320.png`. Synthetic geometric patterns are intentional, not real
listing visuals. Browser validates changed canvas pixels after zoom; a screenshot alone is not the test.

## What is live, fixture, unavailable

- **Real locally:** frontend, HTTP backend, image decode/orientation/derivatives, SQLite persistence,
  cookie isolation, source manifest, revision/publish boundary, panorama WebGL and navigation.
- **Finite provider fixture:** browser Creator rename/reorder and Viewer Q&A. Injection exists only in
  test server, not as a production demo mode. No synthetic AI success is shown on keyless normal startup.
- **OpenAI integration, not live-validated:** text Responses structured parsing with configured model,
  timeout 30s, no SDK retries, 1200 output tokens, store=false. Only typed text and labelled tour metadata,
  never image bytes, are sent when chat is explicitly submitted with a key. No image inspection connected.
- **Audio unavailable:** no licensed music or recorded narration, thus no real two-track ducking/timing
  claim. Play/Pause/voice/music controls show unavailable sources. Device speech is optional and labelled,
  only using a local voice in the tour's source language; unavailable locale/voice is reported honestly.
  Switching checkpoint/locale, opening chat or hiding the page cancels tour speech. Audible output and
  native voice quality were not verified; controls/disclosure tested, not proof of narration/audio delivery.
- **Core unavailable:** panorama is separate camera checkpoints, no mesh/Gaussian/parallax/geometry.
- **HEIC unsupported:** explicit conversion error; JPEG/PNG/WebP validated. No original retention/export
  implementation, crop/inpaint/stitching or fabricated measurements.

## Product context and independent review disposition

Reading list: `PRODUCT-INTEGRATION.md`, integrator-supplied `PRODUCT-CONTEXT.md`, `CHAT-TO-TOUR.md`,
`USER-VIEWS.md`, `TOUR-AUDIO.md`, `CONTRACTS.md`, `BACKEND-HANDOFF.md`.
`PRODUCT-CONTEXT.md` was read from MAIN as supplied context; not edited by this lane. PDF itself was
not copied. It is a problem/JTBD deck, **not hackathon rules**; H0/license/scoring are not derived from it.

1. **Primary renter / buyer only vision:** landing and Creator copy now target rental seekers deciding
   which homes are worth visiting; generic buyer copy removed from the rendered landing.
2. **Creator/Viewer entry and how-to:** separate landing entry links; How it works explicitly creates
   from photos → reviews/publishes → explores published view. Verified route flow in browser.
3. **Avoid reconstruction claims:** removed rendered RECONSTRUCT/3D/360 badge claims. Viewer labels
   cylindrical/provisional coverage, white missing regions and separate viewpoints; no adjacency inference.
4. **One data/AI story:** integrated Creator is server-persisted, assistant is real API or visible missing-key
   failure, test providers are fixture-only; no local heuristic intake in the main user journey. EN/VI
   controls carry across landing/Creator/Viewer. User-authored descriptions remain source language with a
   label. Legacy direct assistant utility stays Vietnamese for compatibility and is unlinked, not a second
   recommended intake. This remaining legacy UI limitation is explicit rather than claimed localized.
5. **Context and evidence:** Viewer shows current scene, Creator-supplied source, editorial order and
   unknown dimensions/adjacency/furniture-fit. No unsupported interview/desk-research impact claims.
   Event panorama mechanics and synthetic checks do not establish rental-shortlisting effectiveness.
6. **Review status:** Claude feedback concerned prior MAIN source and was checked against this branch.
   **No Ag y review received** (trust gate pending); no external review pass is claimed. Tatejo still owns
   independent diff/gate/browser review and merge/deploy decisions.

## Provenance and next owner actions

See `docs/DECLARATION.md §7`. New implementation/tests/docs were Codex-assisted in this worktree;
H0 unconfirmed, so no competition-hours claim. Shared styles/branding/assistant API reused. Renderer
adapted with explicit task permission from team-local `demo-cache/panorama-tour/renderer.js`; no private
images/ZIP/base64 copied. Existing hero license issue remains; no claim that release rights are cleared.

Tatejo: review this branch, rerun the commands, then integrate if accepted. Remaining separately scoped
work: authorized real rental data/value test; permitted OpenAI live test; licensed music + narration and
real audio timing/ducking validation; core/data/GPU feasibility; production/auth/deployment decisions.
No new permission or paid-call request is embedded in this handoff.
