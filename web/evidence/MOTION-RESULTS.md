# UI motion verification — 2026-10-31

`bash scripts/gate.sh web`: lint PASS, six metadata unit tests PASS, build PASS. Contract SKIP (missing fixtures/tour.schema.json); no strict gate claim.

Playwright Chromium: recorded actual Web Animations calls for staggered hero, staggered scroll cards and button press. Confirmed visible settled headline and finite decorative loops. Navigation curtain/arrival, keyboard Enter, browser Back restoration, native hash and modified links PASS. Initial reduced-motion creates no animation; changing preference cancels active effects. Mobile menu, Escape/focus, 320px overflow and no-JavaScript content/native navigation PASS. No browser errors. `motion-check.log`, script `motion-smoke.js`.

Intake regression PASS: English default, Vietnamese persistence, conversation proposal/confirmation, known/unknown Q&A, bilingual extraction, optional metadata form, unsaved form preservation, editable draft, photo upload/preview/removal/invalid rejection, mobile menu, 320–1440px overflow and local image decoding. `motion-intake-regression.log`. The first regression asserted the URL before the new 160ms exit finished; corrected the test to wait for the destination URL, then reran successfully.

Screenshots: motion-hero.png, motion-sections.png, motion-mobile-reduced.png. Screenshots are still frames, not evidence of frame rate; animation assertions above inspect the browser runtime. No real low-end-device FPS benchmark or Safari/Firefox run.

No new packages, assets, API calls or backend changes. Shared build keeps the existing assistant-page output. No production deployment performed in this task.
