# Right-side landing building

Received directly from Thai's annotated screenshot: fade right side to black and add a3D building. From Tatejo's existing frontend ownership; own cwd `.worktrees/landing-model`, branch `feature/landing-model`, basef173106 (includes8K panorama). Shared root/release unchanged.

Implementation: right-side seamless dark gradient; realGLB building rendered on transparent WebGL canvas, no card/frame. Desktop copy stays left. Mobile stacks model below copy within the844px hero at390/320. Model rotates gently; drag or arrow keys rotate manually. One existing pause button controls both panorama and model; interaction pauses both. Reduced motion disables automatic motion. Tab-hidden/offscreen pause; no new API or paid calls. Image/model failure are independent with visible fallback; no fake model load success.

Source: user-provided local3D_Building procedural `sunrise-office-tower-5f-6r.glb` (167588 bytes), copied unchanged. Omit oversized presentation ground slab in preview framing. Clearly labelled building illustration; not the ZInD sample home or photo reconstruction. New narrow native WebGL preview supports supplied baked/matrix triangle GLB, computes normals and honors material colors/transparency; not a general glTF loader. Attribution/declaration in `web/assets/models/README.md`; pre-existing model, newly authored Codex-assisted JS/CSS; H0 unverified. No dependencies or private photo copies.

Changed: web/index.html, app.js, styles.css, assets/models/{building-preview.js,sunrise-office.glb,README.md}; tests/landing-model/{browser-check.js,browser-check.log,gate.log}; this handoff and own task card.

Evidence: strictweb lint/test/build/contractPASS; node--check assets/models/building-preview.jsPASS. Actual Chrome loads supplied GLB, changes rendered pixels on rotation/keyboard/drag; both renderers stop on Pause/reduced-motion. EN/VI caption and1440/390/320 layout no overlap/horizontal overflow.404 image keeps model/pause usable;404 model leaves panorama with honest error. No uncaughtJS errors. Public GET with local source override, no deployment.

Screenshots local only: /private/tmp/landing-model-{1440,390,320}.png. Initial draft /private/tmp/landing-model-first-1440.png; final removes oversized ground slab and corrects transparent backface overlap. No screenshot committed.

NEED: Deploy review/cherry-pick finalSHA using existing integration authority. Existing recursive assets build and /assets static route cover GLB/module; no root/server changes needed. CONTRACT_CHANGE:none. No push/deploy performed.
