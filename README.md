# Estagent — local product preview

Help rental seekers decide which homes are worth visiting. Creators provide photos and descriptions;
viewers explore approved checkpoints and see what is still unknown.

## Run the whole product

Requirements: Python 3.13, [uv](https://docs.astral.sh/uv/) and Node for frontend checks.
From the repository root:

```bash
bash scripts/dev.sh
```

Open **http://127.0.0.1:5180/**. Landing, Creator, Viewer, assets and APIs use this same origin.
The command installs pinned Python dependencies if needed; no `.env` file is loaded automatically.
No key is needed to upload, edit, preview and publish a visual tour. Chat without a configured
`OPENAI_API_KEY` returns an explicit 503. A configured key enables provider calls only on chat submit;
obtain the team's model/data/budget approval before live use. No paid call is part of the tests below.

1. Choose **Create tour**, attach JPEG/PNG/WebP images (≤12 MiB each, ≤20 per tour), and optionally add text.
2. Review scene names, descriptions, order and opening scene. Images default to ordinary photos.
   Select cylindrical panorama only for suitable input and review its explicitly provisional coverage.
3. Save, open the private preview, then check the review/rights checkbox and Publish.
4. Open or copy the published Viewer link. Later draft edits do not change the published snapshot.

Drafts and normalized images survive reload/restart on local disk under `projects/assistant/work/`.
Keep the browser cookie to retain access to your private drafts; this is session isolation, **not login**.
Published tours are listed and viewable by anyone who can access this local server. This preview has
no account system, production hardening or deployment in this task.
`TOUR_DATA_DIR` can select a dedicated writable directory; do not point it at another application's data.

## Truthful limits

- Separate photo/panorama checkpoints; no reconstructed 3D, floor plan, measured dimensions or inferred room adjacency.
- Tour order is editorial. Descriptions are Creator supplied, not independently verified. Furniture fit needs measurements.
- No image understanding connected. Text chat can edit existing labels/order; assistant intake API remains compatible.
- Creator supports authorized recorded narration per scene and background music as PCM 16-bit WAV
  (mono/stereo, supported 8–48 kHz rates, ≤20 MiB and ≤180 seconds per track). Viewer has playback,
  independent music/voice controls and ducking. Missing audio remains explicit; optional **device speech
  fallback** uses the source language. This is not OpenAI narration. See [audio handoff](docs/AUDIO-HANDOFF.md).
- HEIC needs conversion to JPEG. Projection and coverage are never inferred from aspect ratio alone.
- Hero image licensing remains an existing release blocker; see the [asset audit](web/evidence/ASSET-AUDIT.md).
- Synthetic images/demo mechanics do not establish rental-shortlisting effectiveness. The supplied deck is problem/JTBD
  context, not hackathon rules or independently verified outcome research.

## Teammate Generation Studio

`/business/create` is an additional persisted workflow from the teammate branch, separate from the
photo checkpoint Creator above. It stores inputs without a key; generation requires a configured provider.
Spatial and narration reviews are explicit. Without a geometry worker the workflow waits for integration;
it cannot publish a fabricated model. Studio snapshots use their own Viewer and schema. See
[Studio handoff](docs/CREATOR-STUDIO.md) for implementation, fixtures and remaining work.

Production remains a keyless preview. No live OpenAI call or genuine reconstructed model is verified.
API attempt limits are not a dollar cap, and realtime setup limits do not cap stream duration.

## Verify without paid API calls

```bash
npm --prefix web run lint
npm --prefix web test
npm --prefix web run build
uv run --python 3.13 --with pytest --with jsonschema --with-requirements server/assistant/requirements.txt \
  python -m pytest tests/ai -q
# Requires an installed playwright-cli + Chromium. Real local HTTP/browser/SQLite, synthetic images.
uv run --python 3.13 --with-requirements server/assistant/requirements.txt \
  python tests/integration/run_browser.py
bash scripts/gate.sh all --strict
python3 scripts/check_commit_attribution.py --all
```

Strict `all` still fails the baseline **core SKIP** because no reconstruction pipeline exists; it is not hidden.
See [integration handoff](docs/INTEGRATION-HANDOFF.md) for exact checks, evidence, commit and remaining work.
The static build alone cannot host the API; use the single-origin backend command above for the complete flow.

Repo: https://github.com/PhuocDang2104/MLIoT_Estagent_Codex

- Reading list also includes `docs/PRODUCT-CONTEXT.md`, supplied in the integrator checkout: rental-seeker JTBD, evidence limits; not hackathon rules.
- [Runtime contracts and legacy reconstruction draft](docs/CONTRACTS.md)
- [Two views](docs/USER-VIEWS.md), [audio requirement](docs/TOUR-AUDIO.md), [chat-to-tour design](docs/CHAT-TO-TOUR.md)
- [Backend teammate guide](docs/BACKEND-HANDOFF.md), [deployment runbook](docs/DEPLOYMENT.md) (not deployment evidence for this branch)
- [Source/build declaration](docs/DECLARATION.md)

Read `AGENTS.md` before changing code. Never commit keys, uploads or DBs. No Claude attribution trailers;
AI assistance and reused sources still belong in the declaration.
