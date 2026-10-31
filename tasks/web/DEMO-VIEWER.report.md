STATUS: DONE
CHANGED: web/viewer.js; web/viewer.html; web/panorama.js; web/tour.css (Viewer only); web/tests/viewer-camera.test.js; tests/demo-ux/viewer*
EVIDENCE: UV_OFFLINE=1 bash scripts/gate.sh web --strict PASS; camera unit PASS4320 combinations×25rays; Chromium mock-API/real-WebGL+WAV PASS1440/390/320; tests/demo-ux/viewer-results.md and viewer-browser.log
NEED: integrator merge branch including main-sync merge commit; independent real-backend QA and deploy; update old immersive audio harness expecting keyless chat503
CONTRACT_CHANGE: none
NOTES: Base d73ba6a, synced bad806c; no external asset/dependency/paid call. Source transcript language and generated voice labels retained. H0 unverified; Codex-assisted source adaptation; browser uses synthetic fixtures, not live AI.
