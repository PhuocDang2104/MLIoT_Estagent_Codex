# W3 — MinIO integration + keyless production release

Nhận từ Tatejo trong phạm vi Thái đã ủy quyền; bắt đầu 2026-10-31 13:16 Asia/Ho_Chi_Minh, timebox 45 phút. Cwd bắt buộc `.worktrees/release-wave2`, branch `integration/wave2-release`, base `299c2c7`. Root main `5498fdc`; root `.env.example` có edit của user, tuyệt đối không stage/reset.

## Ownership / quyền

Integrator sở hữu deploy/, requirements/root config/docs integration, merge/resolve/main/push thường; nhận handback MinIO wiring và immersive Viewer, không viết đè server/web lane đang làm. Không spawn. SSH/deploy chỉ Estagent; MinIO riêng theo yêu cầu Thái. Root/app credentials sinh riêng, env ngoài Git 0600; không log/copy secret. Không paid API; OPENAI_API_KEY rỗng, ESTAGENT_KEYLESS_PREVIEW=1.

## Acceptance

1. Nối object_storage vào Docker/context/release/native QA, backend MinIO env và network riêng; giữ local/DB blob cũ đọc được.
2. MinIO riêng: private bucket estagent-media, app user policy chỉ bucket, hard bucket quota 512 MiB; service RAM 512 MiB, loopback ports. Kiểm put/get/stat/Range/private denial/restart trên dữ liệu synthetic. Không public bucket/presigned URL hoặc xoá dữ liệu cũ.
3. API guards bật: AI 6/60s concurrency 1, attempts 50/3600s; upload 6/60s concurrency 1. Storage guard /data cap 536870912, free headroom 1073741824. Không mô tả admission như OS quota.
4. Nhận/merge handback hai lane, chạy lại web/AI/schema/rollback tests và browser Creator/Studio/Viewer. Core SKIP là baseline đã biết. Smoke không publish draft tổng hợp; giữ manifest/asset hash public demo trước/sau.
5. Release từ clean accepted SHA đã push main; fetch + attribution checker trước push, không force/--no-verify. Artifact checksum → build VM → config quiet/up --wait → health/TLS/browser. Giữ image/env/data cũ; rollback preflight chỉ đọc standalone backup, không restore volume.

## Release evidence / declaration

Lưu log sanitized ở deploy/evidence/wave3-release/. Ghi final source SHA, image ID, URL, guard configuration không có credential, limits/test/mock/live và phần thiếu. Tooling/integration mới với Codex ngày 2026-10-31; giữ commits/source teammate; H0 chưa chốt, không claim build trong giờ thi. Không model/paid API/production-data deletion.

## Checkpoint 13:27

Backend merged e2e8752 + doc correction92304e1 (adapter415568d included once). Docker/archive/native packaging includes object module. Rollback now requires Creator backup and scans both remote markers (26 tests PASS). AI strict, web strict and native HTTP/config/restart PASS. Dedicated instance provisioned on existing VM only; bucket private, separate app account, hardquota512MiB. Actual quota rejection, synthetic put/get SHA, Range206, anonymous403, unauthorized bucket creation denied and restart persistence PASS. Production assistant unchanged at346a0ba. No old media migration/deletion.

QA corrections: operator mount named operator.py shadowed stdlib; renamed task-specific mount. SDK admin constructor requires keyword endpoint. Initial smoke wrongly required list_buckets denial; MinIO can filter visible buckets to permitted bucket, so acceptance now directly tests unauthorized bucket creation. No application contract changed to satisfy QA.

Evidence: deploy/evidence/wave3-release/{ai-gate.log,web-baseline.log,native-qa.log,rollback-tests.log,minio-restart.log}. Initial minio-live.log records quota PASS followed by the overly strict smoke assertion; corrected restart log supersedes that assertion. Remaining: UI handback, accepted clean SHA artifact/image, actual backend MinIO routes/browser, production rollout/hash preservation.
