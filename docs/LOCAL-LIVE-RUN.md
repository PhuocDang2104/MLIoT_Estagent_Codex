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
