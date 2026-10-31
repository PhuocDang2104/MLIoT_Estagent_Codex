# Khai báo nguồn có sẵn và phần build trong thời gian thi

**Bắt buộc đính kèm bài nộp. Trạng thái: bản kê nháp, chưa xác minh đủ để nộp.**
Dev 1 sở hữu file này; mỗi lead gửi thông tin lane của mình, worker khai trong card/report.
Khai báo không thay thế việc tuân thủ luật cuộc thi hoặc giấy phép nguồn.

## 1. Mốc thời gian và baseline

- Ngày đang làm việc: 2026-10-31, múi giờ `Asia/Ho_Chi_Minh`.
- Ngày/giờ bắt đầu thi chính thức (H0): **chưa xác nhận**.
- Ngày/giờ kết thúc: **chưa xác nhận**.
- Baseline commit ngay trước H0: **chưa chốt**.
- Commit bài nộp cuối cùng: **chưa chốt**.

“Build hôm nay” trong bài nộp phải chỉ rõ phần làm **trong khoảng thời gian thi**.
Code viết cùng ngày nhưng trước H0 vẫn là phần chuẩn bị có sẵn. Chốt baseline tại H0,
ghi cả thay đổi chưa commit hoặc tạo baseline commit trước khi bắt đầu; không bỏ qua file untracked.
Không sửa lịch sử để tạo cảm giác source cũ được viết trong giờ thi.

## 2. Quy tắc phân loại

- **Có sẵn:** code/tài liệu/tooling/model/dataset/asset/cache đã tồn tại trước H0, của đội hoặc bên ngoài.
- **Tái sử dụng có chỉnh sửa:** chỉ phần diff được thực hiện trong giờ thi là đóng góp mới; vẫn ghi nguồn gốc module.
- **Build trong giờ thi:** phần viết mới có bằng chứng thời gian, commit/diff và kết quả chạy; ghi phạm vi file/function/feature cụ thể.
- **Chưa xác minh:** chưa đủ bằng chứng nguồn hoặc thời gian; không được trình bày như phần viết mới.
- Chỉ đọc tham khảo, copy nguyên, adapt và sử dụng dependency/API là các hình thức khác nhau; phải ghi đúng hình thức.
- Khai cả prompt/agent tooling, model pretrained, SDK, dữ liệu đầu vào, demo cache, ảnh, âm thanh và asset được sử dụng.
- API/model ngoài là thành phần sử dụng; chỉ integration/prompt/logic do đội làm mới được kê là đóng góp của đội.
- AI-generated code vẫn phải ghi AI hỗ trợ và thời điểm tạo. Code do AI tạo trước H0 không thành code mới khi commit sau H0.

## 3. Bản kê nguồn có sẵn/tái sử dụng

Các dòng dưới là ứng viên đã thấy trong tài liệu repo, **không khẳng định đã tích hợp vào sản phẩm**.
Trước khi nộp, điền thông tin thật hoặc ghi rõ không sử dụng; thêm dòng cho mọi thành phần còn lại.

| Thành phần | Nguồn/version/commit | Hình thức và phạm vi dùng thực tế | License/quyền dùng | Thay đổi trong giờ thi + bằng chứng |
|---|---|---|---|---|
| House VR Tour tham khảo | `../codex_hack`; URL/commit chưa xác minh | Được tài liệu trỏ làm tham khảo; copy/adapt thực tế chưa xác minh | Chưa xác minh | Chưa xác minh |
| Bộ luật, docs, scripts điều phối | Repo hiện tại; commit baseline chưa chốt | Đã tồn tại lúc lập bản kê; thời điểm so với H0 chưa xác minh | Chưa xác minh | Chưa xác minh |
| OpenAI SDK/API/models/tools | ID/version thực dùng chưa chốt | Mới có rule; chưa có bằng chứng integration chạy thật | Điều khoản dịch vụ/license SDK cần đối chiếu | Chưa xác minh |
| Model/data/asset/cache khác | Chưa kê | Chưa xác minh | Chưa xác minh | Chưa xác minh |

Ghi nguồn public khi được phép; không đưa đường dẫn dữ liệu riêng tư, key hoặc URL chứa token vào bản nộp.
Không đoán license từ tên model. Lưu nguồn license/điều khoản và attribution cần thiết.

## 4. Bản kê build trong thời gian thi

**Chưa có hạng mục nào được xác minh trong bản kê này.** Mỗi hạng mục ghi một dòng; không dùng bảng này làm danh sách tính năng dự kiến.

| Hạng mục hoàn thành | Lane/người phụ trách | File/function và phần mới cụ thể | Có kế thừa nguồn nào? | Commit/diff trong giờ thi | Bằng chứng chạy thật |
|---|---|---|---|---|---|
| Chờ điền sau khi xác minh | — | — | — | — | — |

Chỉ claim phạm vi mà diff và bằng chứng hỗ trợ. Git timestamp là bằng chứng bổ trợ,
không tự chứng minh tác giả hoặc thời điểm viết code; đối chiếu baseline, nguồn gốc và task/report.

## 5. Quy trình đóng bài nộp

1. H0: Dev 1 ghi mốc giờ do ban tổ chức xác nhận, baseline và nguồn chuẩn bị có sẵn; kiểm luật có cho dùng hay không.
2. Mỗi task: worker khai Declaration trong card và `NOTES` của report; lead kiểm diff, chuyển thông tin cho Dev 1.
3. Trước nộp: Dev 1 rà toàn bộ bài nộp, gồm asset/cache/dependency, điền hai bảng và commit bài nộp.
4. README bài nộp phải link file này, tóm tắt phần có sẵn và phần làm trong giờ thi. Slide/demo cũng nói rõ phần tái sử dụng và cache so với live.
5. Còn mục sử dụng thực tế chưa xác minh thì phải công khai giới hạn đó; không đánh dấu declaration hoàn tất hoặc claim phần đó là viết mới.

## 6. Mẫu tuyên bố ngắn cho README/slide

> Nguồn có sẵn: [thành phần + nguồn/version + hình thức sử dụng].
> Trong thời gian thi [H0–kết thúc, múi giờ], đội xây dựng [phần mới cụ thể],
> và chỉnh sửa [phần kế thừa cụ thể]. Bằng chứng: [baseline → commit bài nộp, test/demo].
> AI hỗ trợ: [tool/model, phạm vi]. Demo sử dụng [cache/live, nguồn và thời điểm tạo].
> Bản kê nguồn và giấy phép: docs/DECLARATION.md.

Đây là mẫu cần điền, không phải tuyên bố đã được xác nhận.
