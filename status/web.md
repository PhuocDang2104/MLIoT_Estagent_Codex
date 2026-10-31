# status — lane web (chỉ lead lane web ghi)

- Xong 2026-10-31: FE production https://estagent-weld.vercel.app; Vercel `meetmate/estagent`. Lint/build + browser production PASS; bằng chứng `web/evidence/production-check.log`.
- Chuyển origin sang `PhuocDang2104/MLIoT_Estagent_Codex`: Git remote đúng; Vercel đang thiếu quyền GitHub App (HTTP 400). Repo cũ đã ngắt, auto-deploy tạm dừng; cần chủ repo cấp quyền Vercel. CLI deploy vẫn dùng được.
- Đang làm: Tatejo nhận maintain main + deploy theo chỉ định trực tiếp của Thái; runbook `docs/DEPLOYMENT.md`.
- Kẹt: origin chỉ có main và chưa có BE/core; chờ source BE. Strict gate FAIL vì core/AI/contract SKIP. VM SSH hoạt động, chưa thay đổi stack hay DB đang có.

