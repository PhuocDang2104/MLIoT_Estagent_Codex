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
- Tham khảo: WP River Themes, Aigocy, thư mục `saveweb2zip-com-wpriverthemes-com` do người dùng cung cấp.
- Copy asset: `assets/images/section/hero-1.jpg` → `web/assets/hero.jpg`; font Urbanist normal latin/latin-ext từ bản lưu Google Fonts → `web/assets/`. Giấy phép của bản mẫu chưa được xác minh.
- HTML, CSS, JS, build viết mới với Codex ngày 2026-10-31. H0 chưa xác nhận; không khẳng định đây là phần build trong giờ thi.
- Không tái sử dụng code từ `../codex_hack`, không thêm SDK/API/dependency.

## Kiểm chứng
`scripts/gate.sh web` kiểm cú pháp và build. Contract hiện SKIP vì repository chưa có `fixtures/tour.schema.json`; chưa đủ điều kiện gate strict. Bằng chứng UI trong `web/evidence/`.
