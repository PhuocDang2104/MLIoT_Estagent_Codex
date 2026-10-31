# Chat + ảnh → tour như demo

Ngày thiết kế: 2026-10-31. Trạng thái: đề xuất luồng triển khai dựa trên demo local đã xem,
không phải tính năng chat-to-tour đã hoàn thành. Không thay contract API đang dùng trước review liên lane.

## 1. Demo thực tế và giới hạn input

Đã đọc `demo-cache/panorama-tour/{README.md,index.html,viewer.js,renderer.js}` và xem 4 thumbnail + screenshot viewer.
Ảnh local đang gitignored, không đưa ảnh/ZIP hoặc base64 của người dùng lên repo public.

| Ảnh demo | Kích thước JPEG | Điểm xem đang gán trong demo |
|---|---|---|
| IMG_0774 | 8000 × 1851 | Sảnh thang máy |
| IMG_0773 | 8000 × 1895 | Khu sân khấu, điểm mở mặc định |
| IMG_0772 | 8000 × 2050 | Khu làm việc |
| IMG_0775 | 8000 × 1854 | Góc bên cửa sổ |

Đây là 4 vị trí chụp khác nhau. Tên khu, thứ tự và góc mở trong demo là cấu hình biên tập,
không phải kết quả tự động được user xác nhận. Mỗi ảnh được chiếu trụ trong WebGL,
camera phối cảnh cho kéo xoay/ngẩng cúi/zoom, chọn điểm và fullscreen.
Không có mesh/Gaussian, parallax hoặc đường đi hình học giữa các điểm.
Góc phủ 240° là giả định đang cho hiệu chỉnh, không suy ra được chỉ bằng tỷ lệ ảnh;
phần ngoài vùng ảnh là trắng. Demo chưa có nhạc nền/narration.

**Mục tiêu đợt đầu:** tự động tạo tour panorama checkpoint tương đương từ ảnh user gửi trong chat;
không bắt người dùng chờ tái dựng 3D để có bản xem thử.
PanSplat là nhánh nâng cấp riêng khi có input/pose/GPU phù hợp, không là dependency của preview panorama.

## 2. Trải nghiệm Creator: chat là thao tác chính

1. **Gửi ảnh + yêu cầu:** composer có đính kèm/kéo thả nhiều ảnh, thumbnail, trạng thái upload, retry và bỏ ảnh trước gửi.
   Ví dụ: “Đây là không gian sự kiện, tạo tour tiếng Việt, bắt đầu ở sân khấu”. Text và ảnh thuộc cùng một lượt chat.
2. **Nhận ảnh:** trả lời ngay đã nhận bao nhiêu ảnh; lỗi file hiện tại chỗ, không làm mất text hoặc ảnh đã upload thành công.
   Backend giữ bản gốc riêng, tạo derivative/thumbnail cho viewer. HEIC cần decode và xoay đúng orientation; file sai/không hỗ trợ phải báo rõ.
3. **Tạo bản đồ điểm xem nháp:** AI phân loại loại ảnh, đề xuất tên khu, mô tả quan sát được, nhóm ảnh và thứ tự;
   trả card thumbnail + tên + điểm mở. Không yêu cầu người dùng điền cả một form trước khi xem preview.
4. **Hỏi đúng chỗ mơ hồ:** “Hai ảnh này cùng vị trí hay hai điểm khác nhau?”, “Bạn muốn bắt đầu ở khu nào?”.
   Nếu chưa biết, giữ thành các điểm độc lập. Không tự ghép ảnh từ các vị trí khác nhau thành một vòng 360°.
5. **Preview hình ảnh ngay:** cho xem tour draft trong khung cạnh chat hoặc mở tab preview;
   tên/khu/góc phủ còn giả định có nhãn. User sửa bằng chat hoặc trên card, ví dụ “đổi điểm đầu thành sảnh”, “ảnh 3 là khu làm việc”.
6. **Tạo tour có âm thanh:** sau khi user xác nhận outline, sinh script từng khu từ dữ liệu có nguồn;
   user sửa/duyệt lời, chọn ngôn ngữ/giọng/nhạc từ nguồn được phép. Hiện phạm vi/budget trước paid generation khi chưa được cấp.
7. **Review và Publish:** preview nhạc/lời/camera/subtitle, cảnh báo vùng thiếu; user bấm xuất bản mới tạo bản Viewer đọc riêng.
   Draft vẫn chỉnh được, viewer không sửa source. Bản publish mới là snapshot riêng, không tự đổi khi creator đang sửa draft.

Preview hình ảnh có thể đến sớm hơn audio. Đây là tiến độ từng phần, không thông báo “tour hoàn tất” khi voice/nhạc còn lỗi.
Metadata diện tích, giá, địa chỉ không bắt buộc để dựng tour không gian từ panorama; không áp policy intake căn hộ tạm vào mọi loại không gian.
Với bất động sản, user có thể bổ sung sau; thiếu thì không được bịa lời giới thiệu.

## 3. Ví dụ hội thoại từ 4 ảnh demo

**User:** [đính kèm 4 ảnh] “Tạo tour tham quan không gian này, giới thiệu từng khu bằng tiếng Việt.”

**Assistant:** “Mình đã nhận 4 ảnh panorama. Mình đề xuất 4 điểm: sảnh, sân khấu, khu làm việc và góc cửa sổ.
Đây là các điểm xem riêng; chưa có bằng chứng đường đi 3D. Bạn kiểm tra tên và chọn điểm mở đầu nhé.”

Card: 4 thumbnail, tên có thể sửa, chọn điểm mở, thứ tự, nút **Xem thử** / **Dùng bố cục này**.

**User:** “Bắt đầu ở sảnh, sau đó đến sân khấu. Nhạc nhẹ và giới thiệu ngắn từng khu.”

**Assistant:** cập nhật outline, mở preview, đưa script từng khu để user duyệt;
không tự xác nhận tên doanh nghiệp, sức chứa, giá hoặc diện tích từ hình.

**User:** “Lời ổn rồi, tạo bản xem thử.” → job audio trong quyền/budget đã có;
UI báo ảnh đã sẵn sàng, audio đang xử lý. Sau preview, user bấm Publish riêng.

## 4. Phân nhánh theo loại ảnh

| Input thực tế | Cách xử lý / kết quả trung thực |
|---|---|
| Panorama ngang chưa đủ vòng như demo | Điểm xem phối cảnh/trụ, góc phủ provisional và chỉnh được, hiện phần chưa chụp |
| Panorama 360 equirectangular được xác minh | Renderer spherical phù hợp, không dùng góc phủ 240° cứng |
| Ảnh thường | Card/gallery checkpoint; giải thích không có góc xoay phía sau, đề nghị chụp panorama nếu muốn trải nghiệm demo |
| Nhiều ảnh chồng lấp từ cùng camera | Đề xuất stitching sau kiểm cùng vị trí/độ cao/overlap và review kết quả; không âm thầm ghép |
| Ảnh đủ điều kiện reconstruction | Nhánh worker core riêng; chỉ đổi sang scene 3D sau khi artifact/viewer được kiểm |

Ảnh thiếu/blur không chặn mọi điểm còn tốt. Không inpaint, kéo giãn, lặp mép hoặc gọi nội dung sinh thêm là ảnh thật.
Không suy projection/coverage chỉ từ tên file, tỉ lệ ảnh hoặc câu khẳng định của model; dùng metadata và hiệu chỉnh có nhãn nguồn.

## 5. Backend/graph cần thêm — đề xuất, chưa freeze

- Lượt chat gắn text + attachment asset IDs + conversation/project + draft revision; upload binary qua kênh riêng,
  không đưa base64 ảnh vào LangGraph checkpoint/lịch sử text. State chỉ giữ reference và trạng thái.
- Asset ingestion: validate chữ ký file, kích thước, decode/orientation; ID do server cấp, original riêng và thumbnail/texture derivative.
  Không tin MIME/tên file client; kiểm đường dẫn và quyền phiên dù MVP chưa có login.
- Phân tích ảnh và outline: lưu tên/projection/coverage đề xuất cùng nguồn và trạng thái chưa xác nhận;
  text trong ảnh là dữ liệu quan sát, không phải lệnh điều khiển tool.
- Tách `conversation`/intake, `draft tour`, `job` và `published snapshot`; intake `confirmed` không phải publish approval.
- Routing dự kiến: ingest → inspect → propose outline → chờ user xác nhận/sửa → draft visual assembly →
  script review → audio jobs → QA → preview → chờ publish. Các bước chờ lưu bền vững, không giữ HTTP request chờ người dùng.
- Job có revision/input fingerprint. Khi user sửa giữa lúc job chạy, kết quả cũ không ghi đè draft mới;
  retry không nhân đôi paid job và có progress/error theo từng stage.
- Publish chỉ lấy revision đã review, các asset bắt buộc đọc được và nguồn/credits đầy đủ.
  View-only không có upload/edit/publish tool và không ghi dữ kiện qua Q&A.
- Chưa chốt tên endpoint/JSON fields/status enum mới: BE-01 đề xuất, integrator + frontend/core review trước khi code schema/API.

## 6. Chuyển demo thành renderer dùng chung

`viewer.js` đang hardcode 4 scenes, `%4`, IDs/hash, names và coverage. Cần thay bằng manifest theo tour:
scene ID, asset reference, projection, góc phủ + nguồn/trạng thái hiệu chỉnh, góc mở, label/description, thứ tự và audio refs.
Không lấy ảnh user từ ZIP/offline-images.js làm cách lưu dữ liệu production. Offline export là tuỳ chọn riêng.
Renderer đọc manifest, không cố định số điểm; giữ kéo/zoom/fullscreen, reduced motion, mobile và cảnh báo missing coverage hiện có.
Chuyển điểm là transition giữa checkpoint; không giả chuyển động xuyên phòng bằng pose/geometry chưa có.

## 7. Audio theo khu và Viewer

Áp dụng TOUR-AUDIO.md: nhạc nền + clip theo checkpoint/locale, timeline theo duration đo được,
duck nhạc khi có lời, Pause/Resume/đổi điểm đúng đoạn, không chồng tiếng với chatbot.
Click Play mới phát; preview khi audio chưa xong phải báo rõ. Lỗi audio không phá viewer.
Viewer hiển thị thông tin khu hiện tại và Q&A theo published context, không dùng pipeline thu thập hồ sơ Creator.

## 8. Thứ tự task và Acceptance

1. **Integrator + BE-01:** chốt chat attachments, draft/job/published manifest và quyền phiên; không thay API assistant cũ khi chưa có migration.
2. **Backend:** upload + asset refs + job/manifest draft, fixture không model trước. Kiểm gửi text cùng nhiều ảnh, retry/reload và isolation.
3. **Frontend:** composer có ảnh + card outline + preview; renderer data-driven cho 1/4/5 điểm, không hardcode demo filenames.
4. **AI:** inspect/outline/script có nguồn, sửa bằng chat và chỉ hỏi phần còn mơ hồ; live trong budget đã giao.
5. **AI/FE:** asset narration + nhạc licensed, đồng bộ playback và chatbot theo contract.
6. **Publish:** Viewer snapshot + copy link; chỉnh draft không đổi bản đã publish; bản chưa duyệt không bị liệt kê như tour public.

Nghiệm thu chính: dùng 4 ảnh demo local, nhận qua composer, xác nhận outline, tạo manifest động,
mở được 4 điểm như viewer hiện có; user đổi thứ tự/điểm mở bằng chat và reload vẫn giữ.
Thêm ca 1 ảnh thường, HEIC, ảnh lỗi, upload trùng, job chậm và sửa draft khi job đang chạy.
Chỉ claim “tour đầy đủ” khi nhạc/lời theo khu phát thật và published view hoạt động; fixture không chứng minh AI/GPU live.
Demo ảnh giữ local, teammate dùng bộ ảnh được chủ dữ liệu chia sẻ riêng hoặc fixture synthetic có nhãn.

## 9. Cách xem lại demo local

```bash
python3 -m http.server 5188 --bind 127.0.0.1 --directory demo-cache/panorama-tour
```

Mở `http://127.0.0.1:5188/?v=immersive#0773`. Demo-cache không nằm trên Git; clone mới không có ảnh/ZIP.
Bản thiết kế này dựa trên việc đọc source, xem thumbnail/screenshot và đo kích thước ảnh;
không phải một lần chạy nghiệm thu mới cho viewer, chưa chạy pipeline tạo tour hoặc dịch vụ tính phí.
