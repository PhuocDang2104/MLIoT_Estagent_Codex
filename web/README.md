# Estagent — giao diện

Chạy `npm --prefix web run dev`, mở http://127.0.0.1:5173.
Build: `npm --prefix web run build` → `web/dist/`, deploy dưới dạng website tĩnh.
Không cần cài dependency. Node dùng để kiểm cú pháp/build; Python 3 phục vụ localhost.

Trang chủ lấy bố cục, nền bạc/đỏ, menu nổi, typography lớn và nút nổi từ mẫu Aigocy người dùng cung cấp. CTA mở `experience.html` không qua đăng nhập. Workspace nhận ảnh cục bộ, kiểm loại/kích thước/số lượng và khả năng giải mã ảnh; hỗ trợ xem ảnh lớn và xóa ảnh. Không gửi ảnh lên mạng. Chưa tích hợp backend/3D/AI.

## Bilingual intake (2026-10-31)

- English mặc định; EN/VI trên cả hai trang, chỉ lưu lựa chọn ngôn ngữ vào localStorage. Có fallback khi storage bị chặn.
- Hội thoại cục bộ nhận diện mẫu cơ bản bằng tiếng Anh/Việt: số phòng/ngủ/tắm, diện tích, hướng, cửa sổ, địa chỉ có nhãn `Address:` hoặc `Địa chỉ:` (kết thúc bằng dấu `;` hoặc xuống dòng). Không phải LLM; không suy đoán metadata từ ảnh. Thông tin chưa rõ hoặc câu hỏi không tự trở thành dữ kiện.
- Gợi ý phải được người dùng xác nhận trước khi cập nhật. Form tùy chọn bổ sung tên, địa chỉ, hướng, cửa sổ, phòng, diện tích, ghi chú. Chưa biết giữ trống; không có cửa sổ khác với chưa biết.
- Hỏi đáp giới hạn ở dữ kiện đã xác nhận, thông tin còn thiếu và tạo bản nháp. Bản nháp chỉ dùng dữ kiện đã xác nhận, có thể sửa. Đổi ngôn ngữ giữ nguyên nội dung người dùng. Reload xóa ảnh, chat và metadata; chỉ language preference tồn tại.
- Không gọi API hoặc đổi contract. Cần backend chatbot được phê duyệt để xử lý ngôn ngữ tự nhiên tổng quát, suy luận và sinh nội dung bằng AI thật.
- Ba ảnh nội thất modern minh họa, lưu local; nguồn/tác giả/giấy phép tại [assets/SOURCES.md](assets/SOURCES.md). Không gán ảnh stock thành một bất động sản thật.
- `npm --prefix web test`: kiểm extraction Anh/Việt, phủ định, dữ kiện chưa biết, zero-bedroom, giới hạn số và tính nhất quán. Browser evidence: `evidence/intake-check.log`, `bilingual-home-*.png`, `intake-*.png`.

## Nguồn

### Đồng bộ EN/VI

Landing đã đồng bộ nội dung EN/VI cho luồng ảnh + hội thoại + form; nhãn phụ, meta description, title, alt và aria-label cũng đổi ngôn ngữ. `i18n.js` nghe `storage`, `pageshow` và quay lại tab để không giữ locale cũ khi mở workspace hoặc khôi phục từ Back/BFCache. Chỉ thao tác chọn ngôn ngữ mới ghi preference; đồng bộ không ghi ngược giữa các tab. Storage là tùy chọn: mặc định English, bị chặn vẫn đổi ngôn ngữ được trong trang hiện tại.

EN và VI dùng cùng Manrope variable self-hosted, có đủ 98 ký tự tiếng Việt đã kiểm cmap; không còn trộn Urbanist/Arial cho dấu tiếng Việt. Giấy phép OFL nằm cạnh font. Script locale và CSS được version URL để browser không dùng asset cũ sau lần cập nhật này. Bàn giao đầy đủ, file list và browser evidence: `evidence/HANDOFF-FRONTEND.md`.

### Chuyển động giao diện

`motion.js` + `motion.css` bổ sung hero xuất hiện lần lượt, reveal một lần khi cuộn, hover ảnh/card, phản hồi nhấn nút, mở menu/dialog và fade 160ms khi đi giữa landing/workspace. Trang đích có entrance riêng. Chuyển động trang dùng Web Animations API và CSS, không thêm dependency. Trang vẫn đọc/điều hướng bình thường nếu JS không chạy.

`prefers-reduced-motion` được áp dụng cả lúc tải trang và khi thay đổi trong phiên: bỏ animation, chuyển trang ngay. Trang phục hồi qua Back/BFCache sẽ xóa trạng thái fade. Ctrl/Cmd/Shift/Alt-click, hash links, download, target khác và liên kết ngoài không bị chặn. Trang trí hero chỉ chạy 2 vòng (4.4s), cue cuộn 3 vòng (4.05s); không có vòng animation vô hạn hay vòng xử lý scroll liên tục. Không đo FPS trên thiết bị yếu thật.

Nguồn: code viết mới bằng Codex, tham khảo workflow skill framer-motion-animator, triển khai native cho frontend tĩnh hiện có; không cài Framer Motion. H0 chưa xác nhận. Bằng chứng: `evidence/motion-check.log`, `evidence/motion-intake-regression.log` và `evidence/MOTION-RESULTS.md`.

### Asset và code nền
- Tham khảo: WP River Themes, Aigocy, thư mục `saveweb2zip-com-wpriverthemes-com` do người dùng cung cấp.
- Copy asset: `assets/images/section/hero-1.jpg` → `web/assets/hero.jpg`; quyền sử dụng hero của bản mẫu chưa được xác minh. Urbanist được giữ làm reference nhưng không còn dùng; giấy phép OFL đã bổ sung. Font active hiện tại là Manrope chính thức từ google/fonts; source và license tại `assets/SOURCES.md`.
- HTML, CSS, JS, build viết mới với Codex ngày 2026-10-31. H0 chưa xác nhận; không khẳng định đây là phần build trong giờ thi.
- Không tái sử dụng code từ `../codex_hack`, không thêm SDK/API/dependency.

## Kiểm chứng
`scripts/gate.sh web` kiểm cú pháp và build. Contract hiện SKIP vì repository chưa có `fixtures/tour.schema.json`; chưa đủ điều kiện gate strict. Bằng chứng UI trong `web/evidence/`.
