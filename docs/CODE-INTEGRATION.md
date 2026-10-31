# Quản lý code và tích hợp

Quyết định trực tiếp mới nhất của Thái, 2026-10-31: root Tatejo **chỉ điều phối,
review và nghiệm thu**, không trực tiếp implementation hoặc SSH rollout. Lane
integration/release được giao là owner thực thi tích hợp, resolve, merge/push main
và deploy Estagent; lane UI implement Viewer trên worktree riêng rồi trả handback.
Quyền merge/deploy theo scope user đã giao vẫn hiệu lực, không thêm approval vòng
mới. Tin nhắn điều phối không được giả thành phê duyệt mới của Thái.

Release hiện làm ở `.worktrees/release-wave2`, branch `integration/wave2-release`;
root checkout có edit `.env.example` riêng của user, tuyệt đối không bỏ/stage/reset.
Chỉ đụng instance/container/network/volume Estagent đã được giao trên VM hiện có;
không tạo VM/cloud resource, không thay stack/DB/secret project khác. Giữ keyless,
không paid API. Release production từ SHA sạch đã kiểm và push main; giữ dữ liệu
cũ, rollback phải kiểm cả audio và marker MinIO theo `deploy/rollback_preflight.py`.
Báo về khi chạm quyết định product/contract, biên rủi ro chưa được giao hoặc chưa
phân biệt được fix với reproduce sai; tiếp tục phần độc lập đã được ủy quyền.

## Vòng tích hợp

1. Trước task: fetch main, ghi base SHA, giao owner/Paths/Acceptance và worktree riêng. Không copy secret sang lane.
2. Trước merge: thu SHA/handback, xem diff, chạy lại test/browser theo phạm vi; đối chiếu contract/schema và declaration.
3. Fetch remote trước push; giữ commit đồng đội. Không force-push main, không bỏ lịch sử để né conflict.
4. Conflict kỹ thuật: đọc cả hai phía và consumer/tests, hợp nhất giữ hành vi đã duyệt; không chọn toàn bộ ours/theirs mù quáng.
5. Conflict product/contract: làm hết phần độc lập, báo đúng field/route/hành vi cần quyết; không tự đặt policy mới.
6. Chạy lại gate liên quan sau resolve, kiểm attribution/secret/working tree rồi push thường. Nếu remote đổi trong lúc push, fetch và đối soát lại.
7. Báo SHA main, tính năng thực đã kiểm, phần thiếu và khác biệt GitHub/local/production. Push code không tự đồng nghĩa deploy.

## Trạng thái vòng này

- Production source `e0002f4`, image `ea236835…`, https://estagent.duckdns.org: Viewer glass,2CTA landing, MinIO và Studio runtime đã deploy/kiểm thật. Bằng chứng đầy đủ: `deploy/evidence/wave3-release/release.json`, `status/web.md`.
- Main đồng thời nhận Studio472280f; ancestry guard chặn push cũ. Thái xác nhận được gộp, release lane merge và chạy lại AI/web strict +26rollback tests trước clean artifact/cutover. Không force-push hoặc đụng root `.env.example` riêng user.
- E2E design c33e843 chỉ docs/inventory metadata được merge sau rollout; ZIP/dataset không publish, rights public/export chưa chốt. TTS EN/VI và Video Export được giao lane khác cho phiên bản kế tiếp.
- Không paid AI/geometry/3D reconstruction claim; giữ keyless và guards. Screenshot demo thật local-only; không stage/publish env/DB/user video.

## Đồng đội đồng bộ

Với checkout sạch trên main: `git fetch origin` rồi `git pull --ff-only origin main`.
Đang làm ở branch riêng thì giữ thay đổi, ghi base và đưa PR/handback cho integrator; không reset/force để làm sạch main.
Khi handback phải có branch/SHA, file đã sửa, config/schema thay đổi, test đã chạy, blocker/mock/live và nguồn sử dụng.
Chạy app tích hợp: `bash scripts/dev.sh`, xem README và docs/INTEGRATION-HANDOFF.md.
