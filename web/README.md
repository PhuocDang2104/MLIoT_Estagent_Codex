# Estagent — giao diện

Chạy `npm --prefix web run dev`, mở http://127.0.0.1:5173.
Build: `npm --prefix web run build` → `web/dist/`, deploy dưới dạng website tĩnh.
Không cần cài dependency. Node dùng để kiểm cú pháp/build; Python 3 phục vụ localhost.

Trang chủ lấy bố cục, nền bạc/đỏ, menu nổi, typography lớn và nút nổi từ mẫu Aigocy người dùng cung cấp. CTA mở `experience.html` không qua đăng nhập. Workspace nhận ảnh cục bộ, kiểm loại/kích thước/số lượng và khả năng giải mã ảnh; hỗ trợ xem ảnh lớn và xóa ảnh. Không gửi ảnh lên mạng. Chưa tích hợp backend/3D/AI.

## Nguồn
- Tham khảo: WP River Themes, Aigocy, thư mục `saveweb2zip-com-wpriverthemes-com` do người dùng cung cấp.
- Copy asset: `assets/images/section/hero-1.jpg` → `web/assets/hero.jpg`; font Urbanist normal latin/latin-ext từ bản lưu Google Fonts → `web/assets/`. Giấy phép của bản mẫu chưa được xác minh.
- HTML, CSS, JS, build viết mới với Codex ngày 2026-10-31. H0 chưa xác nhận; không khẳng định đây là phần build trong giờ thi.
- Không tái sử dụng code từ `../codex_hack`, không thêm SDK/API/dependency.

## Kiểm chứng
`scripts/gate.sh web` kiểm cú pháp và build. Contract hiện SKIP vì repository chưa có `fixtures/tour.schema.json`; chưa đủ điều kiện gate strict. Bằng chứng UI trong `web/evidence/`.
