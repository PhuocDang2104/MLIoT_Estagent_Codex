# PRODUCT — đề mặc định: House VR Tour v2

> Đề mặc định dựa trên `../codex_hack`. Có đề thật thì Dev 1 viết lại file này ở H0, giữ nguyên cấu trúc
> (một câu mô tả · demo script · bậc MVP · cut-list). Luật điều phối không đổi theo đề.

## Một câu
Tải ảnh/video căn nhà lên → vài phút sau có tour 3D trên web, AI giới thiệu từng phòng bằng giọng nói, camera bay theo lời.

## Demo script 3 phút (golden path, chạy trên data đã cache)
1. Trang chủ: 1 câu vấn đề + 1 tour mẫu đang chạy (20s).
2. Tạo tour: chọn cách, kéo thả input, bấm Tạo → trang tiến trình 8 bước (40s; job thật chạy nền, chuyển sang project đã cache).
3. Tour: bấm "Nghe giới thiệu" → camera bay theo câu đọc, panel phòng sáng đúng phòng (60s).
4. Panel phòng: nội thất, vật liệu, logic miền (vd. nắng theo mùa) (30s).
5. Một slide số liệu thật: thời gian từng bước, kích thước file, chi phí (30s).

## Bậc MVP

| Bậc | Hạn | Gồm |
|---|---|---|
| **P0 — phải có** | H8 | Upload → tiến trình → tour cho **1 cách nhanh** (A pano hoặc D import file) · AI phân tích phòng thật · lời + giọng · deploy bản tĩnh |
| **P1 — nên có** | H10 | Đồng bộ lời ↔ camera · panel logic miền · cách thứ hai · mobile 390px không tràn |
| **P2 — nếu dư** | sau H10 thì bỏ | Cách nặng (B video→3DGS, C ảnh rời) chạy live · WebXR · Whisper QA giọng |

Cách nặng (B/C) vẫn được **dựng sẵn một tour từ wave 1** để khoe trong demo, kể cả khi không chạy live.

## Cut-list — cắt theo thứ tự này khi trễ
1. WebXR / kính VR
2. Cách C live (giữ tour dựng sẵn)
3. Cách B live (giữ tour dựng sẵn)
4. Panel logic miền → chỉ còn mô tả phòng
5. Giọng TTS → phụ đề chạy theo thời gian
6. Upload thật → nút "Chạy demo mẫu" duy nhất

Không bao giờ cắt: tour mở được, có lời giới thiệu, deploy link sống, README chạy được.

## Giấy phép cần ghi trên slide
Bản tham khảo dùng OmniVoice và VGGT-1B (CC-BY-NC, chỉ demo). Model mới thêm vào phải ghi giấy phép vào `credits` của `tour.json`.
