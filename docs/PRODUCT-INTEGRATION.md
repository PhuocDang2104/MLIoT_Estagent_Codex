# Lane Product Integration

Thái giao ngày 2026-10-31: dọn và nối giao diện/hệ thống thành một sản phẩm thống nhất.
Một writer triển khai: pane `w6G:p1`, nhánh `integration/product-sync`, worktree `.worktrees/product-sync`.
Tatejo giữ review, Git state của main, merge và deploy. Các lane hiện có không sửa cùng vùng của worktree tích hợp.
Đây là uỷ quyền liên lane cho task này, không bị giới hạn vào backend-only/core-only của phân công cũ.

## Kết quả phải quan sát được

Một origin/local command mở được toàn sản phẩm, không yêu cầu user tự chuyển cổng:
Landing → Tạo tour (chat + ảnh) → draft → preview → publish → Xem tour.
Header/footer/font/EN-VI/favicon/navigation thống nhất; Viewer không có edit/publish controls.
Chatbot dùng backend hiện có qua same-origin; thiếu key báo rõ, không trả lời giả.
Viewer dùng dữ liệu draft/published theo manifest động, không hardcode bốn tên ảnh demo.
Audio có controls/duy nhất một giọng phát, không chồng với chatbot; mock/device fallback phải ghi rõ nguồn, không giả OpenAI live.

## Phạm vi và ranh giới

- Đọc root/server AGENTS, docs/CHAT-TO-TOUR.md, USER-VIEWS.md, TOUR-AUDIO.md, CONTRACTS.md, BACKEND-HANDOFF.md.
- Ghi trong worktree: web/, server/, tests/, fixtures/, scripts/, docs/ và config root cần cho dev/build. Giữ compatibility API assistant.
- Có thể bổ sung schema/fixture và route cho vertical slice theo yêu cầu đã giao; ghi rõ contract mới trong docs/CONTRACTS.md và báo thay đổi cho integrator.
- Không thêm auth. Không paid API/model/GPU hoặc copy key; không tự mua asset, đổi provider, SSH/deploy hay chạm stack/DB hiện có.
- Demo tham khảo chỉ đọc ở main `demo-cache/panorama-tour`; chỉ dùng source renderer được phép, ghi provenance. Ảnh người dùng/ZIP/base64 vẫn local, không commit/public.
- Ảnh thường phải hiển thị như ảnh/gallery; panorama thiếu coverage giữ cảnh báo/hiệu chỉnh, không claim reconstruction/360 đủ vòng. Không inpaint vùng thiếu.
- Không thay reference hero khi chưa rõ lựa chọn artwork; ghi blocker quyền ảnh. Không hardcode private path vào app.
- Không sửa file ngoài worktree, không stash/commit nhầm thay đổi main, không merge/push main/force-push. Commit nhánh tích hợp được phép; không attribution Claude.
- Không mở agent/pane khác. Chia nội bộ thành card nhỏ, một pass triển khai và một pass validation. Chưa e2e sau 45 phút/hai hướng lỗi thì báo PARTIAL có căn cứ và điểm tiếp tục.

## Acceptance / bàn giao

1. Một lệnh local trong README: root/Creator/Viewer/assets/API cùng origin; không thiếu motion/favicon hoặc route 404.
2. Browser gửi ảnh synthetic hợp lệ, tạo draft, đổi tên/thứ tự, preview, publish và mở Viewer; reload/restart vẫn đọc tour đã lưu. Không publish draft đang sửa.
3. Mobile 320/390, EN/VI qua các trang, back/navigation/reduced-motion; không JS errors ngoài lỗi cố ý kiểm.
4. API assistant tests cũ giữ xanh, thêm tests cho upload/path/phiên isolation/publish/revision và manifest schema thật; không viết tests chỉ để làm xanh.
5. Audio/missing-key/error states được kiểm và phân biệt fixture/live; không báo đủ audio khi chưa có lời/nhạc thực.
6. Lint/test/build + gate strict (nếu core vẫn thiếu thì nêu baseline, không hạ gate); kiểm attribution; không commit env/upload/db/demo ảnh.
7. `docs/INTEGRATION-HANDOFF.md`: SHA, run command/URL, scope, migration/config, contract changes, evidence, mock/live, còn thiếu và declaration. Không ghi key/cookie/SDP.

Sau handback, Tatejo review diff và tự chạy lại browser/gate trước merge. Hoàn thành lane không tự đồng nghĩa sản phẩm hoàn tất.
