# Landing architecture extension

Owner: web/integration, explicitly requested by Thai to implement, merge and push main.
Base: origin/main 4cec440. Timebox: 45 minutes.
Paths: web/index.html, web/styles.css, web/app.js,
web/assets/architecture/, web/assets/SOURCES.md,
docs/DECLARATION.md, docs/work-items/LANDING-ARCHITECTURE.md,
docs/evidence/landing-architecture/.

Keep existing hero, Seoul media, rotation/keyboard controls, navigation links,
three-step section, footer and English default. Extend below with concise editorial
content inspired by Markdown, accessible Creator/Visitor flow tabs and original
user diagrams in an optional dialog. Retain current/planned architecture distinction.
No runtime/API/dependency/model/config change and no production rollout.

Acceptance: source preservation, web strict gate, browser desktop/390/320,
keyboard tabs/dialog/Escape/focus, image integrity, reduced motion and zero errors.
Visual QA may read public production GET/HEAD media with local browser-only
source overrides; never submit forms, generation, model requests or server changes.
Diagram sources: the two user-supplied PNGs already in docs/. No external art.

Result: web strict gate and isolated local browser acceptance PASS at all five
widths (1440/1024/768/390/320), including keyboard/dialog/focus, reduced motion,
mobile menu and no-JS reading. Evidence: docs/evidence/landing-architecture/.
Existing hero/how/footer HTML and original CSS/JS prefixes are preserved exactly.
Real WebGL interaction was not revalidated by the isolated UI harness; a public
read-only media probe encountered HTTP 502. No runtime/provider/deploy changes.
