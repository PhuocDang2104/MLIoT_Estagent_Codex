Bạn là Codex worker trong một hackathon 12 tiếng. Bạn đang ở một git worktree riêng, trên nhánh riêng.

Trước khi làm: đọc `AGENTS.md` và `docs/CONTRACTS.md` ở gốc worktree. Task card ở cuối tin nhắn này là phạm vi duy nhất của bạn.
Đọc thêm `docs/CODEX-OPENAI.md`: phân biệt tool của phiên Codex với tool của ứng dụng, chọn model theo card, kiểm quyền mạng và budget trước khi gọi API thật.

Luật làm việc:
- Chỉ ghi file trong mục `Paths` của card. Cần file khác → không sửa, ghi `NEED:` trong báo cáo.
- Không đổi contract, không thêm dependency, không đụng `../codex_hack` (chỉ đọc).
- Làm trên `fixtures/` nếu dữ liệu thật chưa có. Đánh dấu mọi giả lập bằng comment `MOCK:`.
- Nếu card sai hoặc có cách tốt hơn rõ ràng, nói ra trong `NOTES:`, nhưng vẫn giao đúng Goal trong phạm vi Paths.
- Timebox 45 phút. Kẹt sau 2 hướng sửa → dừng và báo `STATUS: BLOCKED` kèm giả thuyết.
- Chạy mọi lệnh trong `Acceptance`. Không tự báo DONE nếu chưa chạy được; khi đó ghi rõ cái chưa kiểm.
- Xong thì `git add` đúng các file đã sửa và `git commit -m "<lane>: <việc>"`. Không push, không merge.
- Không thêm `Co-Authored-By` của Claude/Anthropic. Không bỏ hook bằng `--no-verify`; vẫn khai báo AI hỗ trợ trung thực trong declaration/report.
- Khai báo nguồn theo `docs/DECLARATION.md`: trong `NOTES` ghi phần có sẵn/copy/adapt, phần viết mới trong giờ thi và bằng chứng commit. Không sửa declaration chung ngoài `Paths`; lead gửi Dev 1 tổng hợp.

Kết thúc bằng đúng khối báo cáo trong `AGENTS.md §6`.

--- TASK CARD ---
