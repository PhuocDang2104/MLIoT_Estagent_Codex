# Local live evaluation and branch publication

User authorization, 2026-10-31: commit/publish current changes; fix entry/library
and music flow; download licensed placeholder music; use the specified external
environment file's `openAIKey` for one complete real local run. Publication here
means pushing the implementation branch. The local completed tour is published
to the local library. No production VM rollout is included.

Paths: existing HOUSE-MODELING-AGENT scope plus `scripts/local_studio.py`, live
evaluation helpers under `scripts/`, and licensed audio under `web/assets/music/`.
Dependencies remain the existing Python requirements, installed Blender/FFmpeg,
vendored Three.js and Playwright for browser verification.

OpenAI: official Responses and Audio endpoints only. Use a small real ZInD
subset, original images plus an explicitly source-derived layout reference.
Preserve the one-generation/three-review-pass/three-attempt limits. Live launcher
caps Studio provider calls at 40 by default and records usage without prompts,
images or secrets. This is a request cap, not a global dollar budget. Target this
evaluation below USD 5; the team's USD 400 remains a shared total. Record actual
token/audio usage and distinguish estimates from provider billing.

API key stays in the external user-named file and backend process memory. Do not
copy it into the repository, browser, logs, screenshots, git configuration or
command arguments. Git publication must exclude real input data, private SQLite
databases, cookies and credential files. License/credit accompanies bundled music.

Acceptance: home creation opens Studio; library lists Studio and legacy snapshots;
music can be supplied after generation without rerunning AI and is fixed at
publication; placeholder credits appear in the Viewer; one real generation reaches
published with actual OpenAI/Blender/audio and passes browser inspection. Keep the
requested local server running for the user after completion.

## Default model roles (user-selected)

- 3D scene planning: `gpt-6-astra`, `reasoning.effort=high`;
  `OPENAI_MODEL_MODELING` / `OPENAI_REASONING_MODELING`.
- Image observation: `gpt-6.1-terra`, low reasoning.
- Brief, narration and published-tour Q&A: `gpt-6.1-sol`, low reasoning.
- WAV speech synthesis: `gpt-4o-mini-tts`.

All four model IDs were returned by the user's project's Models API on 2026-10-31.
No fallback substitutes another model when access fails. The official model pages
are https://developers.openai.com/api/docs/models/gpt-6-astra,
https://developers.openai.com/api/docs/models/gpt-6.1-terra and
https://developers.openai.com/api/docs/models/gpt-6.1-sol.
Planning allows 24,000 output tokens including reasoning and a 300-second request;
other structured stages allow 6,000 (Q&A 4,000) and 90 seconds. No SDK retries.
Usage ledger counts attempts across local launcher restarts; deleting the private
ledger resets the count. It covers Studio only, not legacy intake/realtime endpoints.

## Local startup

Run from the repository with uv, Python 3.13 and an installed Blender CLI:

```powershell
uv run --python 3.13 --with-requirements server/assistant/requirements.txt python scripts/local_studio.py --env-file "<external dotenv path>"
```

The named key defaults to `openAIKey`; pass `--key-name` for another name.
The launcher checks model access before serving. Data and usage stay under ignored
`projects/local-live/work/`. Open http://127.0.0.1:5180/ for entry,
http://127.0.0.1:5180/business/create for Studio and
http://127.0.0.1:5180/viewer.html for both published tour formats.

`scripts/prepare_zind_demo.py` prepares the source-derived, three-capture open-plan
subset from the existing original dataset + handoff. This is explicitly not a
whole-house reconstruction. `scripts/check_live_studio.py create` makes a paid
generation and refuses a second run when its run manifest exists. It does not
approve reviews. The `preview` and `published` stages make no model calls.

Music: Dream Culture by Kevin MacLeod, CC BY 4.0; 75-second excerpt with fades.
Credit and source are in `web/assets/music/CREDITS.md`. Publication freezes the
current track; music can be replaced before publication without rerunning AI.
