# Context từ Codex-Hackathon.pdf

Nguồn user cung cấp ngày 2026-10-31: `Codex-Hackathon.pdf`, 11 trang, deck Estagent của team MLIoT_Estagent.
Đã đọc text toàn bộ deck và xem trang problem statement. Đây là deck nghiên cứu vấn đề/JTBD,
**không phải thể lệ hackathon**: không chốt hạn nộp, H0, luật source có sẵn hoặc scoring.
PDF chưa được đưa lên Git; không tự publish deck hoặc ảnh người dùng trong demo.

## Định hướng được deck mô tả

- Tagline: “See the space. Understand the place.” Topic: AI-Native Products and Operations.
- User chính: người tìm thuê so sánh nhà online trước khi đi xem; job là chọn nhà đáng đi xem.
- User hỗ trợ: chủ nhà/agent tạo và giải thích listing để người thuê đánh giá đúng.
- Vấn đề: ảnh/mô tả rời rạc chưa giúp hiểu kết nối các phòng, không gian sử dụng và độ phù hợp;
  dẫn tới kỳ vọng sai và nhiều câu hỏi làm rõ.
- Hai view Tạo/Xem tour vẫn phù hợp: Creator cung cấp/duyệt bằng chứng; Viewer hỗ trợ quyết định shortlist.

## Evidence của deck, không phải số liệu sản phẩm đã kiểm

Deck ghi phỏng vấn: 3/4 remote shortlist không hiểu phòng nối nhau; 4/4 muốn floorplan hoặc thêm góc;
2/2 recent viewers thấy khác kỳ vọng; 2/2 listing agents gặp câu hỏi layout và gửi thêm ảnh.
Mẫu nhỏ, không suy rộng thành tỉ lệ thị trường. Các số desk research US/Japan/China là dẫn chứng do deck trình bày;
đợt đọc này chưa kiểm độc lập nguồn/quote/số liệu. Không dùng chúng để claim hiệu quả app.
Deck cũng nói tác động workload của agent chưa được xác minh.

## Tác động đến vòng tích hợp đang chạy

1. Viewer là kết quả chính: tên khu rõ, chuyển khu và biết khu đang xem, thông tin có nguồn, câu hỏi còn thiếu.
2. Creator tạo tour bằng chat + ảnh, xác nhận mapping/điểm bắt đầu/thứ tự/nội dung trước publish.
3. Phân biệt thứ tự tham quan do biên tập với adjacency/đường đi có bằng chứng; không vẽ quan hệ phòng như đo được từ các panorama khác vị trí.
4. Usable space/“đồ có vừa không” cần kích thước hoặc dữ liệu xác minh; ảnh không đủ thì nói chưa biết và đề nghị thêm số đo/góc chụp.
5. Không gọi panorama demo là reconstructed 3D/đo đạc/floorplan thật; dữ liệu demo sự kiện kiểm mechanics, chưa chứng minh giải quyết bài toán thuê nhà.
6. Nhạc/lời từng khu vẫn là yêu cầu của Thái; lời phục vụ hiểu không gian, không chỉ văn quảng cáo. Không làm người xem tưởng dữ kiện AI suy luận là dữ kiện đã duyệt.
7. Không mở thêm feature đo phòng, floorplan/3D reconstruction hoặc market intelligence chỉ vì deck; vòng hiện tại ưu tiên nối vertical slice đã giao.

## Kiểm giá trị sau khi có bản tích hợp

Với dữ liệu nhà được phép sử dụng, yêu cầu người test mô tả khu hiện tại, quan hệ các phòng có bằng chứng,
nêu thông tin còn thiếu và quyết định có muốn đi xem hay không. Ghi nhận câu trả lời trước/sau,
không đặt ngưỡng thành công hoặc công bố kết quả khi chưa có dữ liệu test thật.
