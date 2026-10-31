# PRODUCT-E2E — thống nhất hai role và thiết kế từ demo thật

Owner: Demo/Flow lane, integrator Tatejo. Scope chỉ tài liệu/inventory;
base `6c50572344930f338b83517c908b88edf05dd8f1`, branch `design/product-e2e`.
Paths: `docs/PRODUCT-END-TO-END.md`, card này, optional sanitized
`docs/evidence/demo-inventory.json`. Không ghi runtime, prod, DB, env, media hoặc contract chung.

## Yêu cầu và quyền

User giao kiểm dữ liệu có sẵn `/opt/estagent` trên VM và thiết kế luồng sản phẩm
đầu-cuối, đúng hai entry Creator/seller và Viewer/rental seeker. AI Studio là
implementation bên trong Creator, không phải lựa chọn thứ ba. Read-only SSH và
GET public APIs được giao; không có quyền publish/copy/migrate demo trong task này.
Không đọc private DB/credentials/env/cookie hoặc chạy source trong ZIP.

## Acceptance và kết quả

- [x] Inventory demo thật theo file/type/size/dimensions/duration, phân biệt duplicate/cache/source.
- [x] Đọc bundle README/data contract/provenance; kiểm32JPEG hashes,13MP4 hashes,
  JPEG SOF2048×1024, GLB header/JSON chunk và MP4 mvhd3.917s.
- [x] Đối chiếu public library: một Hackathon snapshot4scene, audio unavailable.
- [x] Thiết kế một Creator pipeline từ chat/ảnh→facts/layout→artifact→audio→review/publish→video,
  Viewer immersive/Q&A, state/error/retry/reload và ownership.
- [x] Nêu API đang có, schema/cap mismatches, cached import/renderer/export NEED riêng.
- [x] Có walkthrough3phút, acceptance hairoles/audio/video và khai source/build hômnay.

Evidence: SSH đọc filenames/ZIP/metadata chỉ tại đường dẫn chỉ định; JPEG/MP4 SHA
so với bundle metadata; GET `/api/tours/published` và publicmanifest. Không browser
render/whole-video-decode trong task này; không model inference, API trả phí, deploy
hoặc thay dữ liệu. Source đọc6c50572 có thể chưa bằng activeproduction khi Deploy
đang rollout; inventory không được dùng như bằng chứng rollout hoàn tất.

## Handoff / không tự vượt phạm vi

NEED integrator xác nhận upstream data/render/model redistribution/export rights,
chốt demo import/copy schema và duyệt room↔capture/projection adapter, thống nhất
hai Viewer schemas, nhận lane video API/format thực trước implementation. Giữ
canonical public snapshot nguyên trạng; Seoul `.filepart` chưa dùng. Không tạo
fixture model hoặc giọngtone để trình diễn như artifact nhà/giọng thực.

Declaration: tài liệu/inspection mới bằng Codex, dựa trên source repo và bundle có
sẵn. Asset/model/cache không được tạo bởi task này; H0 chưa chốt. Không thêm dependency.
