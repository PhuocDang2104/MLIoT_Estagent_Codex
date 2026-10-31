# IMMERSIVE-VIEWER
Owner: frontend worker, assigned by Tatejo within Thái's viewer request.
Base: integration/wave2-release 299c2c7; branch feature/immersive-viewer.
Paths: web/viewer.html, web/viewer.js, web/panorama.js, web/tour.css (viewer-scoped only), tests/immersive/, docs/IMMERSIVE-VIEWER-HANDOFF.md, this card.
Acceptance: default full viewport desktop1440/mobile390/320; no page scroll; truthful cylindrical coverage; pointer/keyboard isolation, panels, navigation/zoom/fullscreen gesture, library/private preview; recorded WAV regression, scene_id chat + honest503; no JS errors; web strict gate; before/after browser evidence.
Baseline: lint/test/build PASS; contract blocked by sandbox uv cache (retry temporary cache).
Reference: user-authorized local Video-48217.mp4, read locally with ffprobe/ffmpeg; production read-only four panorama audit. No video upload, no new/paid assets/deps/API, no publishing.
OpenAI: fixture only; no model/provider calls.
NOTES: existing panorama renderer/assets/font provenance retained. New viewer composition/controls built during this task; H0 classification remains integrator's declaration.

Result: root accepted desktop/mobile direction. Strict web gate PASS; actual Chromium visual/touch, local backend WAV+restart, scene_id POST/keyless503 PASS. Public-demo screenshots moved outside Git to /private/tmp/estagent-immersive-evidence per Thái; only synthetic screenshots committed. Handoff: docs/IMMERSIVE-VIEWER-HANDOFF.md. No contract/dependency/build/server change or deployment.

Follow-up authorized directly by Thái: Apple-style glass for viewer panels/controls. Paths unchanged; CSS-only product change, no new assets/deps/contracts. Browser1440/390/320 + strict gate PASS; evidence local in /private/tmp/estagent-immersive-evidence/glass-*; no demo screenshots committed.
