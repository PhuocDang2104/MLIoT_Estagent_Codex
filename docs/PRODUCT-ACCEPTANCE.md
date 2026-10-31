# Checklist nghiệm thu — sản phẩm tích hợp

Bản checklist do Cursor/Grok soạn trên baseline `da2105d`, chưa đối chiếu toàn bộ với nhánh tích hợp mới. Các nhận xét “chưa có” bên dưới chỉ đúng tại baseline đó; dùng các bước test, không dùng như kết luận hiện tại.

Trạng thái: **chưa nghiệm thu**. Đây là checklist thủ công, không phải biên bản PASS, không có Figma, không đặt API/schema mới và không hạ Acceptance đã viết.

Ngày soạn: 2026-10-31. Worktree `.worktrees/grok-content`, nhánh `review/grok-content`. Điền Đạt / Không đạt / BLOCKED. Ô trống không có nghĩa là đạt. Thiếu bề mặt hoặc contract chưa chốt thì BLOCKED, không đánh Đạt từ đọc code.

## Cách đọc

- **Bắt buộc:** tiêu chí trong `docs/PRODUCT-INTEGRATION.md`, `docs/USER-VIEWS.md`, `docs/TOUR-AUDIO.md`, `docs/CHAT-TO-TOUR.md`.
- **Chưa có:** lúc soạn file, worktree chưa có bề mặt tương ứng. Ghi lại đường dẫn bằng chứng khi người test chạy, không điền sẵn.

## Khai báo AI

Cursor Grok 4.7 soạn file này theo brief Tatejo. Không thêm Co-Authored-By. Không chạy browser, gate, API tính phí hay GPU. Không sửa code ngoài file này.

## Mâu thuẫn nội dung (chưa chọn authority)

1. **3D / camera bay và panorama checkpoint.** `docs/PRODUCT.md` mô tả tour 3D, camera bay theo lời. `docs/Product Proposal.md` mô tả Gaussian Splatting, PanSplat, di chuyển ngoài checkpoint. `docs/CHAT-TO-TOUR.md` §1 và `docs/PRODUCT-CONTEXT.md` mục 5: demo là chiếu trụ/checkpoint, không mesh/Gaussian, không gọi là 3D đã dựng. `web/index.html` ghi “Interactive 3D spaces”, nhãn In development. Vòng này nghiệm thu preview panorama có nhãn góc phủ tạm; không biến proposal 3D thành đã đạt và không xóa yêu cầu 3D khỏi PRODUCT.md.
2. **Form căn hộ và chat + ảnh.** `docs/USER-VIEWS.md` §1: nhập thông tin bất động sản rồi upload. `web/experience.html` là drop ảnh căn hộ JPG/PNG/WebP. `docs/CHAT-TO-TOUR.md` §2: composer chat gửi nhiều ảnh cùng chữ, không bắt form trước preview, không áp diện tích/giá/địa chỉ cho mọi không gian. `docs/BACKEND-HANDOFF.md` §5: `address,area,bedrooms` là policy tạm, chưa chốt sản phẩm.
3. **Một origin và hai cổng.** Acceptance `docs/PRODUCT-INTEGRATION.md` mục 1: một lệnh, một origin. `docs/BACKEND-HANDOFF.md` §4: static `5190`, backend `5180`, `/` backend mở assistant, allowlist chưa phủ motion. `docs/LOCAL-PREVIEW.md`: static `5190`, backend `5191`. `README.md` không có một lệnh mở cả sản phẩm.
4. **Nhạc/lời bắt buộc và schema/asset.** `docs/USER-VIEWS.md` cùng `docs/TOUR-AUDIO.md` xác nhận nhạc nền, lời từng khu, ducking, không hai giọng, EN/VI là narration và phụ đề. `docs/TOUR-AUDIO.md` nói `narration.lines[].room` hiện đã có; `docs/CONTRACTS.md` thực tế đã có field `room` trong `narration.lines[]` (Tatejo đã sửa nhận xét tìm dot-path nguyên văn của reviewer); worktree không có `fixtures/tour.schema.json`. `docs/BACKEND-HANDOFF.md` §2: player/asset/schema nhạc chưa code. `docs/CHAT-TO-TOUR.md` §2 không cho báo tour hoàn tất khi nhạc/lời còn lỗi. `docs/PRODUCT.md` ghi không cắt tour mở được và lời, đồng thời cut-list cho phép hạ TTS còn phụ đề.
5. **Q&A và publish.** `docs/Product Proposal.md` lấy đặc điểm nhận diện từ panorama để trả lời. `docs/PRODUCT-CONTEXT.md` mục 6: không để suy luận AI thành dữ kiện đã duyệt; thiếu thì nói chưa biết. `docs/USER-VIEWS.md` §2 và `docs/CHAT-TO-TOUR.md` §5: Viewer chỉ đọc snapshot đã publish; hội thoại không sửa metadata; `confirmed` của intake không phải publish. Tên route/field chưa freeze.

## Đã kiểm lúc soạn

Đọc năm docs được giao trong worktree và `docs/PRODUCT-CONTEXT.md` ở repo cha. Có `web/index.html`, `web/experience.html`, `web/assistant.html`, `web/assets/favicon.svg`, `web/motion.css`, `web/motion.js`. Không có `viewer.html`, `docs/INTEGRATION-HANDOFF.md`, `fixtures/tour.schema.json`. `web/assistant.js` gọi `/api/assistant/` với `credentials: 'same-origin'`. `web/experience.html` có input nhiều ảnh local. Tìm `publish`, `upload`, `viewer` trong `server/**/*.py`: không khớp. Không mở mạng, không đọc env/cookie. Người giao nói gate build worktree đã PASS; mục K không lấy câu đó làm nghiệm thu sản phẩm.

## A. Same-origin — bắt buộc

- A1. Bước: từ README, một lệnh local mở landing, Creator, Viewer, asset và API. Expected: cùng host và cổng; favicon, `motion.css`, `motion.js` và route đã chốt không 404. Minh chứng: lệnh, URL, mã HTTP các path. Phân loại: bắt buộc; chưa có một lệnh/một origin. Hai tài liệu đang lệch cổng backend `5180` và `5191`.
- A2. Bước: gửi một lượt assistant từ trang cùng origin. Expected: cookie phiên same-origin; origin lạ bị từ chối theo test assistant hiện có; báo cáo không dán cookie. Minh chứng: log network đã che cookie, hoặc log test ghi SHA. Phân loại: bắt buộc với API assistant; gộp landing và Viewer lên cùng origin vẫn chưa có.

## B. Creator gửi nhiều ảnh qua chat — bắt buộc; composer chat chưa có

- B1. Bước: trong composer chat, đính kèm hoặc thả ít nhất hai ảnh hợp lệ cùng một câu, gửi một lượt. Expected: chữ và ảnh cùng lượt; trả lời ngay số ảnh đã nhận; có thumbnail và trạng thái upload. Minh chứng: ảnh chuỗi chat và log số ảnh, không commit binary. Phân loại: bắt buộc theo CHAT-TO-TOUR §2; chưa có trên `assistant.html`.
- B2. Bước: bỏ một ảnh trước gửi, retry một ảnh lỗi, gửi lại ảnh hợp lệ. Expected: lỗi hiện tại chỗ; chữ và ảnh đã nhận không mất. Minh chứng: trạng thái lỗi và lượt gửi lại. Phân loại: bắt buộc; chưa có trên lượt chat.
- B3. Bước: một ảnh thường, một file sai, và HEIC khi decoder đã được giao. Expected: ảnh thường thành gallery và nói rõ không có mặt sau; file sai báo rõ; HEIC đúng chiều xoay. Minh chứng: từng ca, ghi loại file. Phân loại: bắt buộc CHAT-TO-TOUR §4 và §8. `experience.html` hiện chỉ nhận JPG/PNG/WebP. Không tự đặt giới hạn byte mới.

## C. Outline và draft — bắt buộc; contract draft chưa freeze

- C1. Bước: sau ảnh hợp lệ, đọc card outline. Expected: thumbnail, tên khu sửa được, điểm mở, thứ tự, nhãn phần còn giả định; không bắt cả form trước preview; không ghép vị trí khác nhau thành một vòng 360. Minh chứng: card trước và sau một lệnh đổi điểm đầu hoặc thứ tự. Phân loại: bắt buộc thiết kế; chưa có. Dừng nếu contract draft chưa chốt, không bịa field.
- C2. Bước: sửa tên, thứ tự hoặc điểm mở, rồi reload. Expected: draft lưu đúng revision vừa sửa. Minh chứng: trạng thái trước và sau reload. Phân loại: bắt buộc PRODUCT-INTEGRATION Acceptance 2.

## D. Preview panorama — bắt buộc; không nhận 360 đủ vòng hay 3D

- D1. Bước: mở preview draft bằng manifest động, ca một điểm và ca nhiều điểm. Expected: kéo, xoay, zoom hoặc gallery đúng loại ảnh; panorama thiếu coverage còn cảnh báo và góc phủ provisional có nguồn; không inpaint vùng thiếu; không hardcode bốn tên ảnh demo. Minh chứng: ảnh từng loại input và đoạn manifest đã che dữ liệu riêng. Phân loại: bắt buộc; viewer data-driven chưa có.
- D2. Bước: dùng bốn ảnh demo local được phép, xác nhận outline, mở đủ bốn điểm. Expected: bốn điểm xem riêng; tên khu là đề xuất hoặc biên tập, có nhãn chưa xác nhận; không ghi reconstruction. Minh chứng: bốn điểm, nguồn ảnh để local. Phân loại: bắt buộc ca chính CHAT-TO-TOUR §8. Demo-cache không nằm trên Git; thiếu ảnh thì BLOCKED và chỉ thay bằng fixture synthetic có nhãn.

## E. Publish snapshot — bắt buộc; route chưa freeze

- E1. Bước: bấm publish chỉ sau review revision hiện tại, rồi sửa draft. Expected: Viewer mở snapshot riêng; draft đang sửa không bị publish; sửa draft không đổi bản đã publish; bản chưa duyệt không hiện như tour public. Minh chứng: hai bản trước và sau một sửa draft, cùng link Viewer. Phân loại: bắt buộc; chưa có `viewer.html` và không thấy route publish trong `server/`. Checklist không đặt tên endpoint.

## F. Viewer chỉ đọc — bắt buộc

- F1. Bước: từ landing mở tour đã publish và tìm control tạo, sửa, upload, publish. Expected: không có các control đó; chuyển được khu; thông tin đúng khu đang xem. Minh chứng: ảnh Viewer đối chiếu Creator cùng tour. Phân loại: bắt buộc USER-VIEWS §2; entry Viewer chưa có.
- F2. Bước: reload và restart server, mở lại cùng tour đã publish. Expected: vẫn đọc snapshot đã lưu. Minh chứng: log restart và ảnh sau reload. Phân loại: bắt buộc Acceptance 2.

## G. Q&A có nguồn — bắt buộc; spatial Q&A chưa có

- G1. Bước: trên Viewer, hỏi một dữ kiện có trong snapshot và một dữ kiện không có, ví dụ diện tích hoặc giá. Expected: câu có nguồn trích đúng bản đã duyệt; câu không có thì nói chưa rõ; hội thoại không đổi metadata và không thành lệnh sửa tour. Minh chứng: transcript đã lược dữ liệu riêng, kèm chỗ trích trong snapshot. Phân loại: bắt buộc; BACKEND-HANDOFF §2 ghi chưa có spatial Q&A. Tách khỏi intake Creator.
- G2. Bước: yêu cầu tới một khu có trong tour và một khu không có. Expected: chỉ điều hướng khu có trong snapshot. Minh chứng: khu trước, khu sau, và câu từ chối. Phân loại: bắt buộc hướng USER-VIEWS §2. Allowlist chưa freeze: lệch ra ngoài snapshot là Không đạt, không tự đặt schema tool.

## H. Nhạc và lời không chồng — bắt buộc; thiếu asset thì không báo đủ

- H1. Bước: tour có ít nhất hai khu, lời khác nhau, một track nhạc có nguồn và license. Bấm Play mới phát. Expected: nhạc nhỏ hơn lời, giảm khi có lời, trở lại khi hết lời; không hai giọng cùng đọc; đổi khu hoặc tua thì cắt lời cũ và phát đúng khu đích. Minh chứng: ghi âm hoặc log thời gian playback. Screenshot đơn không đủ. Phân loại: bắt buộc TOUR-AUDIO; player, asset và fixture hai khu chưa có. Fixture không chứng minh TTS hoặc nhạc live.
- H2. Bước: mở chatbot hoặc mic khi lời tour đang đọc. Expected: lời tour tạm dừng; không tự chạy hai nguồn lời; chỉ tiếp tục khi người dùng chọn tiếp tục. Minh chứng: thứ tự sự kiện play và pause. Phân loại: bắt buộc.
- H3. Bước: tắt riêng nhạc, tắt riêng lời, đổi EN và VI, rồi Pause. Expected: narration và phụ đề đúng ngôn ngữ đã chọn; Pause dừng cùng trạng thái khu, lời và phụ đề. Minh chứng: hai locale, mỗi locale một câu lời khác nhau. Phân loại: bắt buộc. Thiếu hoặc lỗi audio: có thông báo và phụ đề, viewer vẫn mở, ghi rõ chưa đạt audio đầy đủ.

## I. EN/VI và mobile — bắt buộc

- I1. Bước: trên landing, Creator, preview và Viewer, đổi EN/VI rồi Back. Expected: ngôn ngữ giữ đồng bộ, chữ Việt đọc được, không route 404. Minh chứng: ảnh từng trang ở cả hai ngôn ngữ. Phân loại: bắt buộc Acceptance 3. LOCAL-PREVIEW mới mô tả landing và workspace.
- I2. Bước: viewport 320 và 390, bật reduced-motion, đi từ tạo đến xem. Expected: điều khiển chính không tràn; reduced-motion tắt chuyển động lớn; không lỗi JS ngoài lỗi cố ý của ca kiểm. Minh chứng: ảnh hai viewport và console. Phân loại: bắt buộc Acceptance 3.

## J. Thiếu key, lỗi, retry, reload — bắt buộc

- J1. Bước: chạy assistant không key và gửi một lượt chữ. Expected: báo thiếu key rõ; handoff kỳ vọng HTTP 503; không có câu AI giả. Minh chứng: status và thân lỗi đã che secret. Phân loại: bắt buộc, đã có hướng kiểm. Ca này không gọi API tính phí.
- J2. Bước: gây lỗi tải audio và, nếu job tour đã được giao, lỗi một stage rồi retry trong lúc sửa draft. Expected: lỗi theo stage; viewer còn dùng; retry không nhân đôi job trả phí; kết quả job cũ không ghi đè revision mới. Minh chứng: log stage, error, retry và hai revision. Phân loại: bắt buộc CHAT-TO-TOUR §5 và Acceptance audio. Job tour chưa có thì BLOCKED. Không bịa status enum.
- J3. Bước: reload giữa intake assistant; khi đã có draft thì reload giữa outline. Expected: phần đã lưu còn; phiên không ghi chéo. Minh chứng: trước và sau reload, không dán cookie. Phân loại: reload assistant kiểm được theo handoff; reload draft tour chưa có.

## K. Gate và bàn giao — không hạ chuẩn

- K1. Bước: khi có bản tích hợp để test, chạy lint, test, build và `scripts/gate.sh` strict theo lane. Expected: ghi lệnh và kết quả thật; core hoặc contract còn SKIP thì ghi baseline, không đổi strict để báo xanh. Minh chứng: log gate. Phân loại: bắt buộc Acceptance 6. PASS build mà người giao nêu không thay mục A–J.
- K2. Bước: đọc `docs/INTEGRATION-HANDOFF.md` khi lane tích hợp nộp. Expected: SHA, lệnh, URL, phạm vi, contract, mock hoặc live, phần còn thiếu, khai báo; không có key hay cookie. Minh chứng: đường dẫn file đó. Phân loại: bắt buộc Acceptance 7; file chưa có lúc soạn checklist.

## Giới hạn

Chưa chạy checklist trên browser. Các mục “chưa có” và số cổng phản ánh đọc file ngày 2026-10-31. Live OpenAI, GPU, PanSplat, reconstruction 3D và đo phòng không thay các mục panorama, publish và audio cho đến khi Thái hoặc Tatejo chốt.
