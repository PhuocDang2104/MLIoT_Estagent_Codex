# Hai view người dùng — yêu cầu đã xác nhận

Thái chốt ngày 2026-10-31: sản phẩm có **view Tạo tour** và **view Xem tour**.
Đây là hai luồng giao diện, chưa phải hai loại tài khoản. MVP hiện không cần auth.
Chi tiết hành vi dưới đây là hướng triển khai; route/schema cụ thể do integrator hợp nhất trước khi code.

## 1. Tạo tour — Creator / Business

- Nhập thông tin bất động sản, upload panorama/ảnh và dữ liệu bổ sung được hỗ trợ.
- Theo dõi xử lý scene/checkpoint và AI tạo nội dung.
- Xem trước, kiểm tra và chỉnh thông tin từng khu, lời giới thiệu, nhạc nền và thứ tự tour.
- Phê duyệt rồi xuất bản/chia sẻ tour. Bản nháp không được trình bày như tour đã duyệt.
- Assistant ở view này hỗ trợ thu thập/chỉnh thông tin và tạo tour; không nhầm với chatbot trả lời người xem.

## 2. Xem tour — Viewer / Buyer

- Mở tour đã xuất bản, khám phá scene, chuyển khu/checkpoint và xem thông tin khu hiện tại.
- Phát guided tour: nhạc nền + lời giới thiệu từng khu theo `docs/TOUR-AUDIO.md`.
- Hỏi chatbot về bất động sản/khu đang xem, có thể yêu cầu điều hướng đến khu hợp lệ.
- Có controls phát/tạm dừng, nhạc/lời và ngôn ngữ; không hiển thị công cụ chỉnh sửa/publish của Creator.
- Chỉ đọc dữ liệu tour đã được duyệt; không thay metadata nguồn khi trò chuyện.

## Phân công và Acceptance

- Frontend: hai entry point/luồng rõ ràng từ landing; kiểm browser đi đúng view và không trộn controls tạo/xem.
- AI: tách ngữ cảnh/intents Creator intake với Viewer Q&A/navigation. Không cho câu hỏi người xem trở thành lệnh sửa tour.
- Integrator: thống nhất contract tour draft/published, route và dữ liệu chia sẻ; không tự nâng thành hệ thống auth/role.
- Deploy: phục vụ cả hai view và API tương ứng sau khi route/contract được chốt.
- Hai view không thay thế kiểm soát quyền backend khi triển khai thật; không đưa secret/API key hoặc dữ liệu riêng tư xuống browser.
- Luồng nghiệm thu mục tiêu: Tạo → nhập/upload → draft/preview → duyệt/publish → mở Xem → chuyển khu → nhạc/lời đúng khu → Q&A theo context.
- Đây là tiêu chí triển khai, không phải tuyên bố luồng trên đã hoàn thành. Giữ task hiện tại, trả đề xuất route/contract trước khi mở rộng scope.
