# Rule Codex + OpenAI API

Áp dụng cho mọi Codex worker; lead dùng khi viết card tích hợp AI. Đây là quy ước project,
không thay `Paths`, contract, quyền của runtime hay giới hạn của tài khoản.
Tài liệu chính thức được đối chiếu ngày 2026-10-31; trước khi triển khai phải kiểm lại SDK/model/tool thực tế.

## 1. Codex làm việc trong repo

- Đọc `AGENTS.md` → `docs/CONTRACTS.md` → card → file này. Kiểm nhánh, worktree và diff trước khi sửa; giữ thay đổi có sẵn.
- Một card một deliverable. Không tự spawn worker khác hoặc mở rộng scope. Chỉ song song các thao tác độc lập trong quyền được giao.
- Có `.codegraph/` thì dùng CodeGraph trước khi dò code; nếu không có thì dùng `rg`. Đọc source trước khi sửa.
- Dùng tool hiện có của phiên để đọc/sửa/test; kiểm tool có thực sự được cấp. Không bịa tên tool, kết quả chạy hay quyền mạng.
- Sửa bằng patch nhỏ. Chạy Acceptance; báo rõ fail/skip, fixture/live. Commit đúng file của card trên nhánh worker.
- Lỗi sandbox/auth/network là giới hạn thật: không lách bằng CLI khác, không đổi provider hoặc tự bật quyền rộng hơn.

## 2. Tách hai lớp tool và model

- **Phiên Codex:** model và tool do runtime cấp để viết code, duyệt web, chạy terminal, sửa file.
- **Ứng dụng:** model và tool cấu hình trong request OpenAI API do backend thực thi.
- Có tool trong phiên không có nghĩa app đã tích hợp tool đó. Đăng nhập Codex không chứng minh đã có API key, quota hoặc billing cho app.
- Yêu cầu hiện tại là viết rule; không tự gọi API tính phí để minh hoạ. Card triển khai phải khai báo `Mode`, model, data, host và budget.

## 3. Chọn model theo tác vụ

Đây là khuyến nghị của project, không phải kết quả benchmark hay cam kết quyền truy cập.
Tra [model catalog](https://developers.openai.com/api/docs/models) trước khi chốt ID.

| Tác vụ | Điểm bắt đầu | Điều kiện |
|---|---|---|
| Logic agent, viết lời, coding thông thường | `gpt-6.1-sol` | Mặc định cân bằng chất lượng/chi phí |
| Suy luận khó, lỗi nhiều bước | `gpt-6-astra` | Chỉ nâng cấp khi budget card cho phép |
| Phân loại/trích xuất đơn giản, nhiều request | `gpt-6-luna` | Đạt Acceptance trên fixture đại diện |
| Phân tích ảnh, tác vụ thị giác | `gpt-6.1-terra` | Kiểm input ảnh và output theo contract |
| Studio: dựng kế hoạch 3D từ ảnh/mặt bằng | `gpt-6-astra` / high | User-selected default; `OPENAI_MODEL_MODELING`, `OPENAI_REASONING_MODELING` |
| Giọng nói, transcription, tạo ảnh, embeddings | Model chuyên dụng trong catalog | Kiểm đúng endpoint và định dạng; không dùng ID text thay thế |

- Model chạy Codex do cấu hình runtime quyết định, không lấy bảng app làm cấu hình CLI.
- Model app đọc từ biến cấu hình theo vai trò: `OPENAI_MODEL_TEXT`, `OPENAI_MODEL_VISION`, `OPENAI_MODEL_MODELING`, `OPENAI_MODEL_TTS`. Studio text/vision default low; modeling default high. Live access and budget: `LOCAL-LIVE-RUN.md`.
- Card ghi ID thật; không dùng tên hiển thị hoặc tự suy ra suffix. Chỉ pin snapshot khi tài liệu có ID đó.
- Không tự fallback model/provider. Nếu được duyệt fallback, log model thực dùng và kiểm lại schema/chất lượng.
- Chỉ truyền tham số mà model/endpoint hỗ trợ. Bắt đầu reasoning thấp nhất đủ đạt Acceptance; không mặc định mức cao nhất.

## 4. Chọn API và tool

Dùng SDK chính thức đã được project duyệt; tích hợp text/vision/agent mới ưu tiên Responses API.
Tool chỉ được bật theo allowlist trong card, sau khi kiểm model và endpoint hỗ trợ.
Xem [Tools](https://developers.openai.com/api/docs/guides/tools).

| Nhu cầu | Hướng tích hợp | Quy tắc project |
|---|---|---|
| Thông tin hiện tại bên ngoài | `web_search` | Giữ nguồn/citation, phân biệt suy luận với dữ kiện |
| Tìm trong tài liệu được cấp | `file_search` | Chỉ file/vector store của đúng project và người dùng |
| Gọi logic backend, đọc sensor, chạy pipeline | Function calling | Backend kiểm schema, quyền và target trước khi thực thi |
| Phân tích dữ liệu cần môi trường Python | `code_interpreter` | Không giả định container truy cập được filesystem local |
| Sinh ảnh phục vụ sản phẩm | `image_generation` | Chỉ bật khi deliverable cần ảnh; kiểm budget và hỗ trợ |
| Kết nối hệ thống ngoài | Remote MCP | Server/tool allowlist; tuân thủ approval của hệ thống |
| Điều khiển giao diện | Computer use khi được hỗ trợ | Sandbox và target đã khai; ưu tiên API xác định khi có |

Không bật tất cả tool để thử. TTS/audio dùng API phù hợp trong tài liệu audio, không giả định là tool Responses.

## 5. Function calling và output theo contract

- Dùng [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) cho JSON có schema; validate lại ở backend. Không coi JSON parse được là đúng nghiệp vụ.
- Function tool khai schema chặt, dùng strict khi phù hợp. Áp dụng đầy đủ ràng buộc schema theo SDK/API đang dùng.
- Theo [Function calling](https://developers.openai.com/api/docs/guides/function-calling): xử lý từng call, thực thi qua dispatcher allowlist,
  trả output với đúng `call_id`, bảo toàn context/output items cần thiết, tiếp tục tới kết quả cuối hoặc hết giới hạn.
- Tool arguments là input không tin cậy. Backend kiểm user, project ID, path, URL, miền giá trị; chặn path traversal và SSRF.
- Không đưa shell/SQL tuỳ ý cho model thực thi. Việc ghi/xoá, điều khiển thiết bị hoặc gửi dữ liệu phải qua quyền của ứng dụng;
  model đề xuất hành động không thay thế quyền đó. Không retry thao tác ghi nếu chưa có cơ chế idempotency.
- Chỉ song song tool đọc độc lập; thao tác phụ thuộc/ghi chạy theo thứ tự. Giới hạn vòng agent và tổng tool call.
- Xử lý riêng refusal, response incomplete, lỗi tool và output thiếu; không trả `done` với dữ liệu lỗi hoặc tự bịa field bắt buộc.

## 6. Secret, chi phí và kiểm chứng

- API key chỉ ở backend qua môi trường/secret store. Không đưa vào frontend, biến public, prompt, fixture, screenshot hoặc report.
- `.env.example` chỉ có placeholder. Không commit `.env`, file upload, log chứa dữ liệu hay token. Chỉ gửi input thuộc phạm vi card.
- Live cần đủ host, input và budget. Thiếu thì làm fixture trước, ghi rõ phần chưa kiểm; không hỏi lại quyền đã có trong card/session.
- Áp dụng timeout, giới hạn request/output/tool call/concurrency. Tính cả retry của SDK vào budget; dừng khi chạm trần.
- Retry có giới hạn với lỗi tạm thời/429 theo hướng dẫn API; không retry mù lỗi 400/401/403, quota hết hoặc model không tồn tại.
- Log tối thiểu: task/step, request ID khi có, model thực tế, latency, token usage được API trả, tool và trạng thái.
  Nếu tính USD thì ghi nguồn giá/ngày và phần phí tool liên quan; không suy giá chỉ từ số request.
- Fixture kiểm schema, dispatcher và lỗi. Live smoke trong budget kiểm một đường đi thật; tool call thành công chưa chứng minh pipeline e2e thành công.
- Report `EVIDENCE` nêu lệnh và kết quả thật; `NOTES` ghi fixture/live, model, tool và giới hạn còn lại. Không có key/quota thì ghi chưa kiểm live.
