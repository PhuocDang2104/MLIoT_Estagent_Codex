# Rule cho teammate và agent backend

Kế thừa root `AGENTS.md`. Đọc `docs/BACKEND-HANDOFF.md` → phần API thật trong `docs/CONTRACTS.md` → task card trước khi sửa.
Đây là hướng dẫn portable: không yêu cầu file identity riêng, herdr hoặc CLI của máy Thái.

1. Scope mặc định của backend: `server/`, `pipelines/ai/`, `tests/ai/`; task card quyết định Paths cụ thể. Root/docs/fixtures/web/deploy do integrator hoặc owner tương ứng giữ, cần thay thì trả NEED/patch.
2. Không tạo pipeline reconstruction trong lane backend: adapter worker phải theo contract với core. Chưa có GPU/input thì fixture có nhãn, không bịa output thật.
3. MVP không auth. Tách Creator intake và Viewer Q&A; Viewer không ghi metadata nguồn hoặc tự publish. Không tự đặt policy required fields, quyền publish hay schema mới bằng test/prompt.
4. Giữ tương thích assistant endpoints, cookie path và exact Origin. `confirmed` của intake không phải trạng thái tour đã publish. Đề xuất contract additive + fixture qua CONTRACT_CHANGE trước khi triển khai liên lane.
5. Key chỉ ở backend/env riêng. Không log key, cookie session, SDP, địa chỉ người dùng hay upstream error body. Không đưa service-role key vào browser. Không dùng credential/DB/volume của project khác.
6. Model/tool theo card và `docs/CODEX-OPENAI.md`; model ID mặc định chưa chứng minh access. Card live khai input/provider/budget/timeout/call cap; không coi key hiện có là quyền tiêu tiền vô hạn. Mock và live phải ghi riêng.
7. Job dài trả job ID/progress; retry có giới hạn và idempotency đã chốt, không chạy lại GPU/TTS mù. Không dùng lock trong một process để claim hỗ trợ nhiều worker.
8. Một owner mỗi file. Làm trên nhánh `ai/<task-id>-<slug>`/worktree riêng, không cùng sửa main checkout. Kiểm base và môi trường lane trước khi giao agent; không tự copy secret sang worker.
9. Commit chỉ file thuộc card và kiểm attribution. Không merge/push main, force-push, deploy hoặc sửa lịch sử; integrator nhận bàn giao. Push nhánh cá nhân chỉ khi dev phụ trách giao quyền. Không dùng `--no-verify`.
10. Chạy tests + Acceptance, dẫn kết quả thực. Strict gate còn SKIP phải báo PARTIAL/blocked gate; không xóa test, hạ strict hoặc tạo fixture không có authority để làm xanh.
11. Không spawn thêm agent nếu dev/lead chưa giao. Có nhiều agent thì scope độc lập, không tự điều khiển pane người khác. Timebox 45 phút/hai hướng sửa rồi báo blocker có căn cứ.
12. Khai nguồn có sẵn, phần thay đổi mới và AI hỗ trợ theo DECLARATION; H0 chưa xác nhận nên không claim viết trong giờ thi. Report theo root AGENTS §6, kèm SHA/base, Paths, tests, migration/config mới và NEED.
