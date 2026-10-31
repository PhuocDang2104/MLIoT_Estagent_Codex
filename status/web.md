# status — web/deploy

- CURRENT integrated preview: https://estagent.duckdns.org, source `346a0ba`, image/manifest `deploy/evidence/integrated-vm-release.json`. Backend+pages same-origin, healthy/non-root/read-only/1GB, dedicated volume.
- Verified production HTTP/TLS/Origin/keyless503 and browser upload→draft/save→reload→private preview, VI/mobile320/390 PASS. No paid calls; synthetic QA not published.
- Keyless preview intentionally has no OpenAI text/voice; no real narration/music or core. Old frontend kept healthy for guarded site-only rollback. Prior entries below describe deployment history.

- LIVE 2026-10-31: https://estagent.duckdns.org trên VM; FE v0.2.0 từ snapshot `da2105de1ada4ae865cd5d293553c28c219a4476`, git archive → local lint/test/build → checksum → container static riêng. Không copy source working tree dirty.
- Vercel `meetmate/estagent` đã xóa theo yêu cầu Thái; project API và URL cũ 404. Không nối lại GitHub App.
- Evidence: `deploy/evidence/vm-frontend-build.log` (lint/6 tests/build PASS), `vm-browser-smoke.log` (EN/VI/intake/upload/mobile PASS), `vm-http-check.log` (HTTPS/status/hash PASS), `vm-release.json` (SHA/checksum). Container FE healthy.
- Runtime: namespace/network Estagent riêng, không DB/secret/volume của project khác. Edge đã backup private/validate và chỉ thêm site Estagent, không restart stack khác. Runbook hiện tại `docs/DEPLOYMENT.md`.
- BE assistant CHƯA deploy; `/api/assistant/*` trả 503 JSON rõ ràng. Backend prep native HTTP/SQLite + 9 tests đã PASS tại `9a1e40f`; container BE/live key/model/quota/voice chưa kiểm.
- Hai view Creator/Viewer, publish và audio vẫn là backlog Product Integration; không claim e2e. MVP không thêm auth/Resend. Không dựng Supabase hay đổi checkpoint schema.
- NEED: integrator nghiệm thu/review/commit thay đổi deploy mới, cập nhật root còn nhắc Vercel; chốt contract/routes hai view/audio, BE config/budget và container acceptance trước release tiếp. Lane này không commit/push/stash/spawn.
- Declaration: deploy tooling mới bằng Codex; FE source/asset từ snapshot đã có, không copy Minute/House VR Tour, không paid API; H0 chưa chốt. Quyền hero reference còn ở audit frontend, không claim license mới.
