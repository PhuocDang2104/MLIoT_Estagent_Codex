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

- Đã merge nhánh `integration/product-sync`: same-origin Creator/draft/preview/review/publish/Viewer.
- Đã giữ và merge commit đồng đội `23504e9` (chuyển/bổ sung tài liệu LangGraph và UI workflow), không có conflict nội dung khi merge.
- Đã cập nhật release allowlist/Docker để chứa tour backend và frontend mới; native QA PASS, chưa build/release container tích hợp.
- Core reconstruction còn thiếu; nhạc/narration thật và OpenAI live chưa nghiệm thu. Không gọi sản phẩm hoàn tất chỉ vì test visual PASS.
- `docs/Business Workflow Langgraph/` là bộ design mới của đồng đội, không phải toàn bộ feature đã triển khai trong bản panorama hiện tại.
- PDF/demo ảnh/ZIP/env/DB giữ local, không được stage/publish. Không push nhánh backup chứa attribution cũ.

## Đồng đội đồng bộ

Với checkout sạch trên main: `git fetch origin` rồi `git pull --ff-only origin main`.
Đang làm ở branch riêng thì giữ thay đổi, ghi base và đưa PR/handback cho integrator; không reset/force để làm sạch main.
Khi handback phải có branch/SHA, file đã sửa, config/schema thay đổi, test đã chạy, blocker/mock/live và nguồn sử dụng.
Chạy app tích hợp: `bash scripts/dev.sh`, xem README và docs/INTEGRATION-HANDOFF.md.
