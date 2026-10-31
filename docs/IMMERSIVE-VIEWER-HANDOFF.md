# Immersive Viewer — handoff cho Tatejo / Deploy w6F:p1

Nhận từ Tatejo trong phạm vi Thái giao; root đã duyệt hướng UI desktop/mobile.
CWD: `/Users/anhoaithai/Documents/AHT/1. PROJECTS/CodexHackathon/.worktrees/immersive-viewer`.
Branch: `feature/immersive-viewer`; base/commit trước task: `299c2c7` (`integration/wave2-release`).
SHA bàn giao: xem commit chứa tài liệu này (`git log -1 --oneline`).
Không sửa root checkout/.env.example, main, server, contract, build/package; không push/deploy.

## Đã làm

- `web/viewer.html:4`: viewer mở tour mặc định phủ viewport; title/back/locale trên mép, tên khu/phụ đề dưới trái, navigation và các panel Details/Stops/Audio/Chat thu gọn. Library vẫn là document layout; private preview có nhãn riêng và không có published chat/edit/publish.
- `web/tour.css:12`: CSS mới chỉ áp dụng `[data-page=viewer].is-immersive`; 100dvh/safe areas, glass/gradient đọc rõ, panel tự cuộn và vừa 320px, focus/reduced-motion. Không cần CSS mới trong build/static allowlist.
- `web/viewer.js:84`: FOV ban đầu theo aspect/chiều cao ảnh đã chụp, không kéo giãn texture. Trên mobile, ảnh tiếp tục phía sau overlay. Giới hạn yaw theo coverage; không quấn thành 360°. Chuyển checkpoint fade 240ms, giữ frame khi ảnh kế tiếp đang decode; reduced-motion bỏ fade.
- `web/viewer.js:123`: Fullscreen API chỉ qua click, bao gồm controls/panels; Escape đóng panel/trả focus hoặc thoát fullscreen. Layout phủ viewport vẫn giữ sau khi thoát API fullscreen. Canvas nhận drag/wheel/arrows, nhập chat không điều khiển camera.
- Giữ nguyên WAV/music/narration, mute/gain/ducking, pause/no-autoresume khi mở chat, source-language disclosure và API `scene_id`. Không đổi schema sang `active_scene_id`.
- `web/panorama.js:3`: vùng ngoài ảnh là nền trung tính tối, không sinh/nối nội dung thiếu; phép chiếu cylindrical/coverage không đổi.

## Tham chiếu và audit

Đã đọc local video Thái cấp `/Users/anhoaithai/Downloads/Video-48217.mp4` bằng ffprobe/ffmpeg: 16.018912s, 720×1280. Xem toàn chuỗi 3s và chuỗi 0.5s đoạn 6–10s. Áp dụng phần nội thất khoảng 7–10s/15s: ảnh chiếm màn hình website, chữ nhỏ sát mép, tên khu dưới trái và controls dưới phải. Không copy viền đen màn quay điện thoại; không mô phỏng dollhouse/tầng hay dùng asset từ video. Không upload video; không cần Instagram (chưa xem reel trực tiếp).

Production audit GET-only đủ 4 checkpoint, đều cylindrical 240° provisional. Before desktop ảnh nằm dưới header/title, khoảng y483; after stage x0/y0,1440×1000. Mobile trước fit FOV có vùng không được chụp ở mép; sau fit ảnh phủ sau overlays mà coverage vẫn giữ240°.

Ảnh chứa demo thật **chỉ lưu local**, không commit theo yêu cầu Thái:
`/private/tmp/estagent-immersive-evidence/`:
- `before-desktop.png` và `after-reference-desktop.png`: cùng checkpoint Khu sân khấu.
- `after-1440.png`, `after-390.png`, `after-320.png`: viewport cuối.
- `details-vi-390.png`, `library-320.png`, `touch-mobile.png`, `captured-boundary-mobile.png`.
Log visual/touch ghi path lúc chạy; ảnh đã được chuyển khỏi worktree trước commit. Harness hiện ghi ảnh demo thẳng vào thư mục local trên.

## Bằng chứng chạy thật

- `tests/immersive/evidence/gate-web.log`: `bash scripts/gate.sh web --strict` PASS lint/test/build/contract. Baseline lint/test/build PASS; lần contract đầu bị sandbox/cache/DNS, chạy với cache uv hiện có đã PASS; không bỏ qua gate.
- `tests/immersive/evidence/visual-browser.log`: Chrome, source frontend worktree override + production GET-only. Stage và document đúng 1440×1000 /390×844 /320×740; không page overflow; drag/zoom/arrows, thumbnails/prev/next, gesture fullscreen/Escape, close/focus panels, center hit target, EN/VI, reduced-motion, library, zero JS errors.
- `tests/immersive/evidence/touch-browser.log`: Chromium mobile emulation có touch events thật qua CDP; drag thay đổi pixel, nhập chat không đổi camera, không page scroll, yaw chạm biên không wrap, zero JS errors. Chưa chạy trên thiết bị iOS vật lý.
- `tests/immersive/evidence/browser.log`: app/backend local thật, SQLite tạm, upload/decode WAV tổng hợp; hai volume/mute, duck .25→.05 và .4→.08, pause/resume, rapid scene changes, subtitle, chat pause/no-autoresume, locale mismatch, lỗi tải WAV, draft/private preview, server restart và anonymous published WAV. Fixture là sine tone, không phải giọng/nghệ sĩ hay audio OpenAI.
- Chat được kiểm trên backend local không key: request POST mang `scene_id` đang xem; response503 và thông báo hiển thị. Production không nhận POST/chat/upload từ audit.

Chạy lại:
```sh
bash scripts/gate.sh web --strict
uv run --offline --python 3.13 --with-requirements server/assistant/requirements.txt python tests/immersive/run_audio.py
playwright-cli -s=immersive open about:blank
python3 tests/immersive/run_visual.py
```
Preview local đang phục vụ tại `http://127.0.0.1:5197/viewer.html?tour=f9c9100bf6effa0f141594dd972bed6d`.
Khởi chạy lại: `python3 tests/immersive/preview.py --port 5197` (chỉ proxy GET public; không dùng làm server production).

## Declaration / phần còn thiếu

Tái sử dụng viewer/player và renderer đã có trên299c2c7 (renderer có attribution ngay đầu file), Manrope tự host/OFL theo `web/assets/SOURCES.md:17`, ảnh demo/URL hiện có của Thái. Không thêm dependency/font/ảnh/API có phí. Viết mới bố cục/overlay, camera fit/interaction và harness bằng Codex trong task này; audio harness adapt từ `tests/audio/`. H0 chưa xác minh, không tự khai toàn bộ code là build trong giờ thi. Screenshot synthetic có thể commit; screenshot demo thật giữ local.

NEED Deploy w6F:p1: review/cherry-pick SHA bàn giao, gate integration và rollout theo quyền của Deploy; không cần thay asset allowlist/build/server.
CONTRACT_CHANGE: none.
Blocker implementation: none. Chưa deploy; QA mobile là Chrome emulation, không phải iPhone thật.

## Follow-up trực tiếp của Thái — Apple-style glass

Thái yêu cầu đổi chất liệu panel/nút theo screenshot. Chỉ sửa CSS viewer trong `web/tour.css`: nền kính trong có tint, blur28px/saturate160%, phản sáng gradient/viền/inset shadow, nút chọn trắng kính, ô nguồn bo mềm. Giữ nguyên layout, nội dung, API, camera/audio/chat; không thêm asset/dependency. Có prefix WebKit và nền đục fallback khi không hỗ trợ blur hoặc giảm transparency.

Đã chạy lại strict web gate PASS và Chrome mở/đóng cả4 panel ở1440/390/320, không overflow/JS errors. Bằng chứng **chỉ local**: `/private/tmp/estagent-immersive-evidence/glass-gate.log`, `glass-browser.log`, `glass-1440.png`, `glass-390.png`, `glass-320.png`. Không stage ảnh chứa demo thật. Commit follow-up có parent `b0849df`; Deploy nhận riêng patch CSS/docs này theo quyền hiện có.
