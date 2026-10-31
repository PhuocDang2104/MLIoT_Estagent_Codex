# Panorama nội thất bổ sung — CC0, chưa đưa lên production

Research ngày 2026-10-31; ưu tiên P0 ZInD đang tích hợp, không thay demo canonical.
Đề xuất **Lebombo** đầu tiên: phòng sinh hoạt trống, ánh sáng rõ, phù hợp xem panorama
nội thất; **Entrance Hall** cho demo không gian kiến trúc. Mỗi source là một demo độc lập.
Không nối các ảnh từ nhiều địa điểm thành một căn nhà hoặc tạo adjacency/measurements.

## Nguồn/quyền đã kiểm trực tiếp

[Poly Haven asset license](https://polyhaven.com/license) áp dụng CC0 cho chính HDRI
assets, cho dùng thương mại và redistribute. Không lấy ví dụ render/logo/ảnh người dùng
trên website làm asset vì phạm vi quyền của các nội dung đó khác. Tải đúng file
**Tonemapped JPG** từ official files API, không lấy screenshot hoặc image thumbnail.

[API Terms](https://github.com/Poly-Haven/Public-API/blob/master/ToS.md) đã đọc: request
dùng User-Agent `EstagentHackathonResearch/1.0`; API live tích hợp vào sản phẩm cần
credit nguồn nhìn thấy được. Asset CC0 đã tải/self-host không bắt buộc attribution,
nhưng nên giữ tên tác giả/Poly Haven/CC0 trong credits và source ledger.
[Official FAQ](https://docs.polyhaven.com/en/faq) mô tả HDRI của thư viện là ảnh
equirectangular 360×180°. Đây là projection evidence bên cạnh nguồn HDRI của từng
asset, không chỉ suy ra từ tỷ lệ2:1. JPG tone-mapped là LDR, không còn dải sáng HDR.

## Shortlist bốn nguồn

| Asset/source chính thức | Nội dung và tác giả | Official JPG | Tình trạng |
|---|---|---|---|
| [Lebombo](https://polyhaven.com/a/lebombo) | Phòng sinh hoạt trống; Greg Zaal | 1,873,244 bytes;8192×4096 | Đã tải, MD5 khớp API, xem ảnh trực tiếp |
| [Entrance Hall](https://polyhaven.com/a/entrance_hall) | Sảnh kiến trúc cổ điển; Sergej Majboroda | 4,284,028 bytes;8192×4096 | Đã tải, MD5 khớp API, xem ảnh trực tiếp |
| [Artist Workshop](https://polyhaven.com/a/artist_workshop) | Xưởng họa sĩ; Oliksiy Yakovlyev | 5,156,645 bytes;8192×4096 | Đã tải, MD5 khớp API, xem ảnh trực tiếp; demo studio riêng, không gọi là listing nhà ở |
| [Small Empty Room 1](https://polyhaven.com/a/small_empty_room_1) | Phòng nhỏ trống; Sergej Majboroda | API báo28,316,012 bytes; site ghi8K JPG | Chưa tải; vượt12MiB, cần normalize trước dùng |

Chỉ ba JPEG đầu được tải, tổng11,313,917bytes. Không download HDR/EXR, không gọi
imagegen/model hay upload dữ liệu user. Ba ảnh đã mở bằng image viewer, nội dung
khớp source; chưa kiểm nghiệm bằng renderer Estagent trong lane research này.

## File handoff cho integrator

Tất cả file chỉ ở `/private/tmp/estagent-demo-candidates/`, không vào Git:

| Filename | SHA-256 của file original |
|---|---|
| `lebombo.jpg` | `2e70777b9947b8a74809c22b9485bea6c4d67955e1ab2747507890b429eb1e9b` |
| `entrance_hall.jpg` | `4cf8de63a3243a9a761c542db839924a408a4f5bbfe2ed4c9a829d8c760b48a4` |
| `artist_workshop.jpg` | `3d1a24d3255246fd53a3eeefca5b30dc0540c62406dd5be93ada1912557f61b1` |

`download-metadata.json` cùng thư mục có official download URLs, tác giả, kích thước,
SHA và license. Bản sanitized metadata có trong [evidence](evidence/demo-asset-candidates.json).
Các đường dẫn tmp là file đã download, chưa phải asset URL sống hoặc source runtime app.

**NEED trước import:** ba file8192×4096 có33,554,432pixels, vượt giới hạn32M của
legacy image upload dù mỗi file nhỏ hơn12MiB. Chuẩn hóa local bằng resize không sinh
nội dung xuống4096×2048 (hoặc2048×1024), strip metadata, giữ original hash và ghi hash
derivative riêng. Lane này chưa resize hoặc đổi code/upload cap. Không cần chuyển
HDR/EXR vì official JPG đã có. Không ép ảnh này vào cylindrical renderer; dùng
equirectangular sphere/source-confirmed projection của renderer phù hợp. Không đánh
dấu geometry/GLB, room connections hoặc video mới đã tạo từ một ảnh HDRI.

Tạo demo entry riêng từng nguồn, owner-copy khi Creator dùng dữ liệu mẫu, public
publish chỉ theo scope integrator đã duyệt. Narration/music chưa có: cần asset có
quyền hoặc TTS theo budget riêng. Dùng mô tả quan sát được; không thêm địa chỉ,
giá/diện tích, chủ nhà hoặc lời chào bán chưa được cung cấp.

Evidence: official license/API terms + asset pages đã mở; public API files/info,
download≤3 originals; kiểmlen/MD5/JPEG SOF/SHA và xem cảba ảnh. Không sửa prod,
không thay canonical demo, không phát sinh API tính phí. Source assets có sẵn của
Poly Haven, research/source ledger viết mới bằng Codex hôm nay; H0 chưa xác nhận.
