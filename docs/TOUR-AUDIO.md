# Audio tour — yêu cầu sản phẩm

Thái yêu cầu ngày 2026-10-31: **mỗi tour có nhạc nền và giọng giới thiệu thông tin từng khu vực**.
Trạng thái: yêu cầu đã xác nhận; hành vi chi tiết dưới đây là mặc định triển khai đề xuất, chưa phải tính năng đã chạy.

## Trải nghiệm và tiêu chí bàn giao

- Tour có một track nhạc nền và các đoạn lời giới thiệu gắn rõ room/checkpoint ID.
- Bấm bắt đầu tour mới phát âm thanh. Có Play/Pause, tắt/bật nhạc, tắt/bật lời và điều chỉnh âm lượng riêng.
- Mỗi khu có lời riêng dựa trên metadata/quan sát được duyệt: tên khu, đặc điểm và điểm nổi bật. Thiếu thông tin thì bỏ qua hoặc nói chưa rõ; không bịa diện tích, giá, vật liệu.
- Nhạc nền nhỏ hơn lời; tự giảm khi có lời/chatbot nói, khôi phục khi hết. Không để hai giọng đọc chồng nhau.
- Camera/checkpoint, đoạn lời và phụ đề cùng một trạng thái phát; Pause dừng đồng bộ. Chuyển khu hoặc tua phải ngừng lời cũ và phát đúng khu đích, không xếp hàng các đoạn cũ.
- Khi người dùng mở hội thoại, tạm dừng lời tour; chỉ tiếp tục tour khi người dùng chọn tiếp tục. Không tự khởi động hai nguồn lời.
- Thiếu/lỗi audio phải có thông báo và phụ đề; viewer vẫn dùng được. Đây là fallback lỗi, không được báo đã đạt yêu cầu audio đầy đủ.
- Nhạc dùng nguồn được phép sử dụng/phân phối, có nguồn và license trong declaration/credits. Không tự mua nhạc hay gọi dịch vụ tạo nhạc/TTS tính phí khi budget chưa rõ.
- Bản EN/VI dùng narration và phụ đề đúng ngôn ngữ đã chọn; không chỉ đổi nhãn điều khiển.

## Phân công và contract

- AI: chuẩn bị script theo từng room/checkpoint, audio và duration/timing thực tế; phân biệt fixture với audio sinh thật.
- Frontend: player hai lớp nhạc/lời, controls, đồng bộ khu/camera/phụ đề, ducking và ngăn chồng lời với chatbot.
- Deploy: phục vụ audio asset đúng MIME, kiểm đường dẫn và quyền truy cập như các asset tour.
- Tatejo: hợp nhất schema/fixture với contract chung. `narration.lines[].room` hiện đã có; nhạc nền và audio từng khu cần proposal additive được review, không tự đổi `tour.json` giữa các lane.
- Đây là yêu cầu kế tiếp trong backlog; không ngắt Acceptance của card đang chạy hoặc tự sửa file ngoài ownership hiện tại.

## Kiểm chứng cần có

1. Tour mẫu có ít nhất hai khu với lời khác nhau và một track nhạc có nguồn rõ.
2. Browser phát audio thực từ asset; kiểm nhạc giảm khi có lời và không chồng hai giọng. Screenshot đơn lẻ không chứng minh audio chạy.
3. Kiểm Pause/Resume, đổi khu nhanh, tua, tắt từng track, chuyển ngôn ngữ và lỗi tải audio.
4. Kiểm mic/chatbot đang hoạt động không bị lời tour chen vào; ghi rõ audio thật, fixture, model live hoặc phần chưa kiểm.
