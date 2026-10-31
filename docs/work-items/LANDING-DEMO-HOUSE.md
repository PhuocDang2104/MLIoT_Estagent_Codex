# Correct hero model to the demo house

Direct Thai correction: “lấy khung nhà 3D demo á”. Replace office illustration with actual demo dollhouse; keep dark fade/layout.
Own worktree .worktrees/landing-demo-house, branch feature/landing-demo-house, base8833355.
Paths: web/index.html, web/app.js, web/assets/models/, tests/landing-demo-house/, docs/LANDING-DEMO-HOUSE-HANDOFF.md, this card.
Use existing manifest.dollhouse.url without API/schema changes. Preserve actual geometry/base textures, controls, EN/VI, responsive layout, reduced motion. No GLB/photos/screenshots in Git. No server/deploy/new dependencies.
Acceptance: actual Chrome requests demo manifest/model, renders house layout, rotation/drag/keyboard/pause, desktop1440/mobile390/320, honest asset failure, strict web gate.
