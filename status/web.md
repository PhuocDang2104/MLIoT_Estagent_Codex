# status — lane web (chỉ lead lane web ghi)

- Xong 2026-10-31: FE production https://estagent-weld.vercel.app; Vercel `meetmate/estagent`. Lint/build + browser production PASS; bằng chứng `web/evidence/production-check.log`.
- Chuyển origin sang `PhuocDang2104/MLIoT_Estagent_Codex`: Git remote đúng; Vercel đang thiếu quyền GitHub App (HTTP 400). Repo cũ đã ngắt, auto-deploy tạm dừng; cần chủ repo cấp quyền Vercel. CLI deploy vẫn dùng được.
- Deploy vòng 1 nhận từ Tatejo (`w6B:p1`): chuẩn bị tại `deploy/`, không commit/push/stash/spawn/deploy production; source kiểm `9a1e40f89e2afa1a5e0ec2671a21187ff4efe723`.
- Đã làm: Dockerfile/Compose namespace riêng, env placeholder + fail-fast config, health/smoke không gọi model, release guard yêu cầu main sạch, rollback và HTTPS/FE proxy proposal trong `docs/DEPLOYMENT.md`. BE assistant đã có trên main; dùng SQLite một worker, chưa có adapter Supabase. MVP không thêm auth/Resend.
- Evidence: native HTTP + SQLite PASS (no-key và fake-key), 9 tests assistant PASS; Compose config PASS, missing-key/dirty-release guard PASS. Log `deploy/evidence/local-check.log`, `deploy/evidence/preflight.log`.
- Kẹt: Docker daemon local chưa chạy nên chưa build/container/volume/rollback; chờ SHA tích hợp sạch, endpoint/DNS/TLS và owner root/edge tích hợp proxy. Model/key/budget/policy cần owner chốt trước live. Vercel link vẫn null; không connect lại mù. Không đổi stack/DB/secret/volume hiện có; không dựng Supabase.
- Declaration: deploy tooling mới bằng Codex, giữ requirements/asset có sẵn; không copy Minute/House VR Tour, không gọi API trả phí. H0 chưa xác nhận. Chi tiết và NEED ngoài Paths ở runbook.

