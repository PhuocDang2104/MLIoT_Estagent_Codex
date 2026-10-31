# Bilingual intake verification — 2026-10-31

`bash scripts/gate.sh web`: lint, six Node tests and static build PASS. Contract still SKIP because repository has no fixture schema; strict gate is not claimed.

Playwright: English default; Vietnamese switch and persistence across reload/pages; photo upload/view/remove/invalid rejection; chat extraction from English and Vietnamese; explicit confirmation before metadata changes; Q&A from confirmed fields; unknown information handled without invention; optional form; editable draft retained across locale changes; mobile navigation; no horizontal overflow at 320, 390, 768 and 1440px. All three local apartment images decode. No browser errors. Log: intake-check.log; script: intake-smoke.js.

Images are lazy-loaded. Initial image assertion ran before scrolling to the gallery; updated smoke scrolls each image into view and waits for decode before asserting/capturing. No asset failure.

Scope: local UI preview, rule-based extraction, no OpenAI/backend call. Metadata schema is internal to UI, not an API contract. No user input persisted or sent externally. Photo sources and usage: ../assets/SOURCES.md. H0 unconfirmed.
