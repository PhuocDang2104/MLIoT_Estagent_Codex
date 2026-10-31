# Landing panorama clarity

Direct request from Thai; isolated worktree `.worktrees/landing-sharp`, branch `feature/landing-sharp`, base662d2b9. Prior demo controls handoff7417714 remains separate.

Audit: current catalog panorama is2048×1024, only about398 source pixels across a70° view, visibly enlarged on desktop. Read local3D_Building reference: councilroom3200×1276 with no local provenance; room samples1024×512. Neither solves crisp fullscreen residential imagery.

Change: original Poly Haven / Greg Zaal Lythwood Lounge8192×4096 CC0 JPEG,5.03MB. Local static asset, no third-party runtime request. Desktop GPU texture ceiling8192 (subject to device limit); mobile4096. Render DPR up to2. Existing rotation/pause/drag/reduced-motion retained; initial view faces lounge windows. Landing shows bilingual illustrative-panorama credit; sample CTA continues to existing ZInD tour, no suggestion that background is its photo. No backend contract changes.

Source declaration: https://polyhaven.com/a/lythwood_lounge — asset predates competition, CC0 license checked on source page. Unmodified original JPEG. Existing renderer adapted, new Codex-assisted frontend changes. No code copied from3D_Building, no paid APIs/dependencies/user uploads. H0 unverified.

Evidence: tests/landing-sharp/gate.log and browser-check.log. Chrome source-overrides against production GET, not a deployment. Screenshots local only: /private/tmp/landing-sharp-before.png, /private/tmp/landing-sharp-{1440,390,320}.png. Initial reduced-motion assertion raced the browser media-change event; harness now waits for actual button state before pixel stability check.

NEED: Deploy review/cherry-pick final SHA under existing integration authority. Asset lives under existing recursively built/served assets directory; no server allowlist or build change.5MB original favors detail; mobile GPU upload is reduced but network download remains5MB. CONTRACT_CHANGE:none.
