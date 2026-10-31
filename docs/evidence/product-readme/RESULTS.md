# Product documentation review — 2026-10-31

Scope: product README, Vietnamese product introduction and the two supplied PNGs.
No application code, environment, dependency, API contract or deployment changes.

- Reviewed current Studio/Blender, Viewer/chat, export and Studio + Seoul release
  documentation. Product architecture goals are distinguished from current runtime.
- Both Markdown files successfully rendered by GitHub's Markdown REST API in GFM mode.
- 56 relative links/images/anchors resolved in the repository (33 README, 23 writeup).
- Chromium preview: both documents at 1280, 390 and 320 pixels; all images loaded,
  no horizontal page overflow and no page errors. Four screenshots are included.
  Preview uses GitHub-rendered HTML and local review CSS, not the live GitHub site.
- Both user-supplied 1920×1080 PNGs kept byte-for-byte; SHA-256 in validation.json.
- `bash scripts/gate.sh web --strict`: PASS lint, tests, build and fixture contracts.
- `git diff --check`: PASS. No paid model calls or production mutations were submitted.

Layout references and image provenance are recorded in docs/DECLARATION.md and
the product writeup. No prose, logos or cover artwork were copied from reference READMEs.
