# UI verification — 2026-10-31

`bash scripts/gate.sh web`: lint PASS, build PASS, contract SKIP (missing fixtures/tour.schema.json). Strict contract validation remains unavailable.

Playwright Chromium, localhost: CTA opens experience.html directly; image upload, preview dialog, Escape, individual removal, clear all and invalid image rejection PASS. Mobile navigation open/close PASS. No horizontal document overflow at 390px or 320px. No console errors or page errors during the successful smoke run.

Screenshots: desktop.png, mobile.png, workspace.png, workspace-mobile.png. Script: smoke.js; execution: browser-check.log.

Scope: frontend only, no backend/API/3D/AI tested or implemented. Input images stay in browser memory. Reference assets and declaration: ../README.md.
