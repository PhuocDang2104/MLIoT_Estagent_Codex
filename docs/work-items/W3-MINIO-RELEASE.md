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

## Checkpoint 13:31 — real application + multipart

Candidate source4cd00f0, image d32df244577fa4ae80b1b49f8d62685b0b4411574f13a9b3711a4f1a130ee1f2 built from committed archive (not production rollout). Actual MinIO SDK + FastAPI routes with temporary SQLite: upload/dedupe/private401, isolated review/publish (no real public site), audio Range206/416, Studio empty BLOB + remote marker, restart readback and disabled-backend503/no fallback PASS. Extra private WAV5600044 bytes/175seconds used two-part multipart ETag; cross-part Range, full SHA, restart and unauthenticated401 PASS. No provider mocks or paid calls. Public baseline current manifest matches prior wave2 raw hash; four scenes/eight image+thumbnail SHA saved outside Git for after-rollout comparison.

Thái's direct role update recorded in AGENTS.md and docs/CODE-INTEGRATION.md: root Tatejo coordinates/reviews/accepts, release lane executes authorized integration/deploy, UI lane owns Viewer; no new approval round.

## Final integration gate

Immersive Viewer b0849df merged preserving teammate commit; root accepted desktop/mobile direction. Final web strict and AI strict PASS after merge. Hard quota now also verified that existing synthetic media remains readable while new writes are denied. Video Export9:16/16:9 explicitly stays next release. Production smoke extends private Creator draft with real PCM upload/play/pause; Viewer audit uses deployed files only (no route override), screenshots with real demo remain local. Final artifact/release evidence follows after rollout.

## Production checkpoint and directly requested UI hotfix

Source6c505723/imagefd0e9835 deployed from clean main clone/checksummed artifact. Actual production Creator+private PCM playback, Studio save/reload, Viewer1440/390/320/fullscreen/panels/keyboard/drag, TLS and all8old image/thumbnail hashes PASS. Viewer test initially timed out waiting for CSS animation after resize with default RAF polling; same condition reproduced and passed with timer polling, then full deployed-file audit PASS. No application change made to satisfy that test.

Production SQLite confirms3tour remote markers +1Studio marker, no duplicate Studio BLOB. Fresh standalone backups cause legacy rollback preflight to correctly refuse346a0ba (remote counts reported). Root's role remains coordination/review/acceptance.

Direct Thái follow-ups: landing exactly2hero CTA Create tour/Tạo tour and View tours/Xem tour, Creator entry preserved; remove standalone Studio hero CTA, retain Studio route/backend. Index ownership explicitly assigned; body Creator CTA wording made consistent, no redesign. CSSglass dee0618 merged preserving lane commit, same JS/API/layout/assets. Hotfix webstrict and local-HTML browser EN/VI1440/390/320, correct entries and Studio200 PASS. Final production hotfix verification follows; Video Export remains next release.

## Handoff complete

Received from Tatejo; cwd `.worktrees/release-wave2`. Production accepted source37962a3/image7bcd22d5, HTTPS healthy. Backend92304e1, Viewerb0849df/glassdee0618, landing2CTA and user-confirmed Studio472280f integrated. Final AI/web strict +26rollback PASS; actual MinIO multipart/quota/private/Range/restart, production Creator/Studio/Viewer/landing/chat503, exact deployed-file bytes and original public hashes PASS. Snapshot metadata+objects consistent,10SQLite verified; no secret exposure/paidAPI/newVM/data restore/deletion. Designc33e843 docs-only merged after rollout; no ZIP/dataset. See release.json/logs. No release blocker; TTS/Video next lane, geometry/iOS/core remain explicitly outside acceptance.
