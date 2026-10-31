# P0 Landing / Creator — handoff Tatejo và Deploy

Nhận trực tiếp từ Tatejo theo scope Thái; cwd `.worktrees/pitch-ux`, branch `feature/pitch-ux`, base `2ae4506`. Không chạm worktree immersive-viewer, Viewer/server/deploy/package. Không push/deploy.

## Đã làm
- `web/index.html`: thay hero generic bằng lời hứa cụ thể (EN/VI), hai CTA `Explore the sample home` → `/demos/zind-house-000` và `Create your tour` → `/creator.html`. Bỏ Pexels gallery, slogan lặp, PHOTO sticker/✦/red-dot/vertical caption và badges developer. Gộp thành flow3 bước với minh hoạ nhãn đúng chức năng, không giả screenshot/3D reconstruction.
- `web/app.js`: đọc GET `/api/demos`, dùng `thumbnail_url` thật của descriptor zind-house-000; chỉ nhận URL same-origin. Khi ảnh chưa có, giữ link canonical và placeholder chữ; không thay bằng ảnh bất động sản khác. Không tự dịch facts.
- `web/styles.css`: layout responsive scoped `.pitch-landing`, style custom dropzone Creator; không đổi Viewer.
- `web/creator.html/js`: một button dropzone keyboard Enter/Space gọi file input sr-only; input không còn native Choose Files lộ. Ẩn saved-drafts khi session chưa có draft. Badge AI không hiện onload; lỗi sau action vẫn dùng notice/API như cũ. Studio vào mục tuỳ chọn chuẩn bị nội dung trong flow Creator. Link sample là hành động thật, không giả seed.
- EN/VI dùng `data-vi` và i18n hiện có. Không auth; giữ đúng JPEG/PNG/WebP12MB và20ảnh theo form/validation hiện có.

## NEED EXACT cho Deploy
1. Sample import: chưa có seed API đã chốt. Nút hiện tại chỉ **xem tour nhà mẫu**, không hứa thử ảnh tạo draft. Cần route import vào owner session để copy4 ảnh nguồn có quyền từ catalog vào `/api/tours/assets` và trả manifest checkpoint-tour-v1 hợp lệ (hoặc chốt dùng existing binary upload path). FE chưa tự thêm API/schema; không dùng thumbnail làm nguồn panorama.
2. TTS3298792: đã chừa `<div id="narration-panel"></div>` trong draft editor sau scene-cards. Deploy nối `mountNarrationPanel` theo docs/TOUR-TTS-HANDOFF, chỉ refresh khi id/revision thay đổi; không mount placeholder hay gọi paid TTS từ patch này.
3. Video7797ef0: giữ patch exportlink sau publish khi tích hợp. Diff creator.js ở đây chỉ hook dropzone và hide-empty list, không sửa handler publish; `<div id="export-panel"></div>` chừa sau published-link.

## Evidence / declaration
Baseline gate do root xác nhận PASS; gate chạy lại trong own worktree PASS lint/test/build/contract (`tests/pitch-ux/gate.log`). Browser kiểm source worktree qua route override, production GET-only; keyboard picker dùng PNG tổng hợp, không gửi file lên production. Log xác nhận `tests/pitch-ux/browser-final.log`; log lượt đầu ghi native chooser rồi tiếp tục bằng CLI upload (harness được sửa selector nhiều attachment). Screenshot nhà thật chỉ ở `/private/tmp/pitch-ux-*.png`, Creator `/private/tmp/pitch-creator-*.png`, không Git. Upload backend không đổi; browser lần này kiểm picker/attachment preview, không claim production draft upload.

Nguồn: font Manrope/OFL và code i18n/motion hiện có; ảnh hero từ actual catalog do Deploy cung cấp, không Pexels mới/paid assets. Code/CSS/copy viết mới trong task, minh hoạ flow chỉ HTML/CSS; không claim thời điểm H0. Contract change: none trong patch; seed import là NEED chưa chốt.

Final browser PASS:1440/390/320 EN/VI,2CTA,keyboard picker/attachment preview,empty drafts hidden,zero JS errors. `catalog.log` xác nhận thumbnail thật và canonical200. Trường heroLoaded0 trong lượt Creator là count ở trang Creator, không phải lỗi tải hero; kiểm hero riêng tại catalog.log. Fix input sr-only bị CSS form kéo rộng đã reproduce1540px và retest không overflow.

## Yêu cầu trực tiếp tiếp theo: hero full màn hình và xoay

Thái bác card ảnh tĩnh: đổi hero thành panorama toàn viewport (100dvh), header/copy/2CTA overlay; bỏ card và caption riêng. Dùng chính thumbnail catalog ZInD equirectangular đã xác nhận ở `web/demos/house.html` của release, không suy full360 từ demo cylindrical240° trước đây. `web/app.js` thêm camera WebGL equirectangular, adapt phép chiếu từ `web/studio-panorama.js` hiện có; không sửa renderer Viewer/Studio. Xoay tự động chậm, kéo để xem/dừng xoay, nút pause/resume có keyboard; reduced-motion hiển thị góc tĩnh, dừng rAF khi page ẩn/hero ra khỏi viewport. Nếu WebGL không dùng được, hiện ảnh gốc và giữ CTA; không mua/thêm ảnh/dependency.

Evidence mới: `tests/pitch-ux/panorama-browser.log` xác nhận pixel đổi khi xoay, đứng yên khi pause/reduced-motion, hero x0/y0 và đúng1440×1000,390×844,320×740, hai CTA giữđúng,zero JS errors. `panorama-gate.log`: strict web PASS. Screenshot nhà thật **local only** `/private/tmp/pitch-panorama-{1440,390,320}.png`. Patch follow-up này tiếp nối d07e869; không đổi Creator/TTS/export/server.
