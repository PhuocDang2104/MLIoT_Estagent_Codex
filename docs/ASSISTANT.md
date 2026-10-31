# Estagent — hội thoại thu thập thông tin bằng LangGraph

Trạng thái 2026-10-31: đã triển khai riêng tại `/assistant.html`, kiểm bằng LangGraph thật + SQLite thật + model/network mô phỏng. **Chưa kiểm live OpenAI, chưa deploy backend, chưa nối workspace intake cũ.** Repo có phiên khác chỉnh sửa/commit đồng thời; phần này không thay logic intake cũ.

## Chạy local

Python 3.13 là môi trường đã kiểm. Dependency được pin theo bản đang có trên máy, không cài thêm vào môi trường toàn cục.

```bash
python3 -m venv /tmp/estagent-assistant-venv
/tmp/estagent-assistant-venv/bin/pip install -r server/assistant/requirements.txt
# Tạo .env.local theo .env.example; điền key ở máy chủ, không đưa vào frontend.
/tmp/estagent-assistant-venv/bin/python -m uvicorn server.assistant.app:app \
  --env-file .env.local --host 127.0.0.1 --port 5180
```

Mở `http://127.0.0.1:5180/assistant.html`. Máy hiện tại đã có dependencies; có thể dùng trực tiếp `python3 -m uvicorn ...`. Không có key: trang hiển thị “Chưa kết nối OpenAI” và không tạo câu trả lời AI giả. Không cần key để xem thiết kế. Có thể khởi động không có `--env-file` để kiểm trạng thái này.

Biến môi trường:

| Biến | Mặc định / mục đích |
|---|---|
| `OPENAI_API_KEY` | Key backend; không gửi về browser |
| `OPENAI_MODEL_TEXT` | `gpt-6.1-sol`, Responses structured output |
| `OPENAI_MODEL_REALTIME` | `gpt-realtime-2.1`, WebRTC nhận audio và đọc phản hồi |
| `OPENAI_MODEL_TRANSCRIBE` | `gpt-transcribe` |
| `ASSISTANT_ORIGIN` | `http://127.0.0.1:5180`, exact origin cho POST |
| `ASSISTANT_REQUIRED_FIELDS` | `address,area,bedrooms`; **đề xuất tạm**, chưa được Thái xác nhận |
| `ASSISTANT_DB` | `projects/assistant/work/checkpoints.sqlite`, ngoài web và gitignored |

## Luồng

`START → understand → validate → required / optional / clarify / help / review / complete → finish → END`

- `understand`: OpenAI diễn giải câu tự nhiên thành schema Pydantic gồm patch, intent, trường thu hồi và câu hỏi làm rõ. Không dùng regex để giả lập LLM.
- `validate`: kiểm miền giá trị, nhất quán số phòng; câu mơ hồ hoặc patch sai không cập nhật hồ sơ. Nhận nhiều dữ kiện trong một lượt. Giá trị 0 của studio vẫn hợp lệ.
- `required`: hỏi từng thông tin bắt buộc còn thiếu. Bỏ qua không làm hồ sơ được đánh dấu đủ; người dùng có thể dừng và quay lại.
- `optional`: hướng dẫn ngắn và cho bỏ qua từng mục / tất cả mục còn lại.
- `review`: chỉ xin xác nhận khi đủ bắt buộc và đã xử lý/bỏ qua các tùy chọn.
- `complete`: người dùng đã xác nhận; sửa dữ kiện sẽ bỏ trạng thái xác nhận và yêu cầu kiểm tra lại.
- SQLite checkpointer lưu sau các node; request tiếp theo tiếp tục trên cùng `thread_id`. Mỗi lượt kết thúc ở END chờ tin mới, không giữ HTTP request mở trong lúc chờ người dùng. Không cần `interrupt()` cho việc chờ tin nhắn giữa các lượt.
- Cookie HttpOnly ngẫu nhiên ánh xạ phiên vào thread, sống 30 ngày. Tải lại trang/khởi động lại backend vẫn giữ hồ sơ. Mất cookie không khôi phục được từ UI hiện tại; chưa có tài khoản hoặc đồng bộ đa thiết bị.

Các trường dùng cùng ý nghĩa với `web/property.js` nhưng **không sửa contract project/tour**. Bắt buộc được cấu hình độc lập. Giá/nội thất hiện ghi vào `notes`, chưa có field riêng.

## Giọng nói dùng cùng graph

Chat chữ → `/api/assistant/turn` → LangGraph. Voice → WebRTC transcription → cùng endpoint turn → cùng LangGraph → hiển thị chữ → Realtime đọc câu trả lời của graph. `create_response: false` ngăn voice model tự trả lời thay graph. Giọng đọc vẫn là model sinh audio: chưa đo độ chính xác đọc nguyên văn.

Chỉ xin quyền micro khi người dùng bấm nói; tắt/end/pagehide giải phóng track. Khi đang xử lý hoặc đọc, mic tạm mute để tránh phản hồi âm thanh. Có nút dừng phát, bật/tắt đọc phản hồi và kết thúc voice. Bản này là luân phiên nói/nghe; chưa hỗ trợ tự ngắt lời bằng giọng nói. Quyền micro bị từ chối hoặc voice lỗi vẫn chat chữ được. UI đóng voice sau 5 phút; đây không phải giới hạn billing phía server.

## API độc lập

| Endpoint | Nội dung |
|---|---|
| `GET /api/assistant/state` | Tạo cookie nếu thiếu; đọc profile, deferred, history, required, labels, stage, confirmed, reply, configured |
| `POST /api/assistant/turn` | JSON `{text, request_id}` → cùng shape; tối đa 2.000 ký tự; request ID cuối được chống lặp |
| `POST /api/assistant/voice` | `application/sdp` → SDP answer từ OpenAI; key không ra client |

HTTP body tối đa 64 KB, OpenAI timeout 30s, không retry SDK tự động; text cap 1.200 output tokens, voice cap 512 tokens. Chỉ request dữ liệu text người dùng và audio đã bật; không gửi ảnh trong workspace. Không bật tracing LangSmith, tool call hoặc provider khác.

Đây là backend **local một worker**. Exact-origin/cookie không thay thế xác thực production. Trước deploy cần gắn auth, rate limit/budget theo user, chính sách lưu/xóa checkpoint và HTTPS. FE Vercel hiện chỉ build file tĩnh; muốn chạy chatbot trên đó cần proxy `/api/assistant/*` tới backend. Không tự thêm deployment/đổi route trong task này.

## Apify do Thái cung cấp

Đã nhận tài liệu `compass/crawler-google-places`. Vai trò đề xuất: enrichment tùy chọn về trường học/bệnh viện/siêu thị quanh vị trí người dùng, lưu nguồn và thời điểm lấy dữ liệu riêng với profile đã xác nhận. **Chưa tích hợp hoặc chạy Actor**; câu hỏi về mục đích sử dụng đang chờ trả lời. Không dùng dữ liệu doanh nghiệp để suy diện tích, số phòng, pháp lý hoặc giá của căn hộ. Khi triển khai: nêu giá và giới hạn trả phí trước paid run, dùng query/area có phạm vi, tắt review/contact/lead enrichment không cần thiết, xử lý job dài ngoài HTTP chat turn.

## Kiểm chứng và nguồn

- `python3 -m pytest tests/ai/test_assistant.py -q`: 9 pass; LangGraph và SQLite thật, extractor và OpenAI voice network là fixture. Có một cảnh báo deprecation từ dependency LangGraph đã cài.
- `node --check web/assistant.js`: pass.
- `playwright-cli -s=assistant run-code --filename=web/evidence/assistant-smoke.js`: pass. Desktop 1440, mobile 390/320; sửa/bỏ qua/xác nhận/lỗi và voice lifecycle với WebRTC giả lập. Console có HTTP 502 cố ý để kiểm đường lỗi; không có JS pageerror.
- `bash scripts/gate.sh web --strict`: lint/test/build pass, **strict fail** do thiếu `fixtures/tour.schema.json` đã tồn tại trước task.
- `bash scripts/gate.sh ai --strict`: compile/pytest pass trong môi trường uv nạp requirements backend; **strict fail** cùng fixture contract còn thiếu. Gate được cập nhật để không chạy AI tests trong môi trường thiếu dependencies.
- Screenshots: `web/evidence/assistant-desktop.png`, `assistant-mobile.png`, `assistant-no-key.png`.
- Chưa kiểm chất lượng hiểu tiếng Việt, quyền model/quota hoặc audio live; máy chưa có `OPENAI_API_KEY`, `.env` hoặc `.env.local` khi kiểm.

Tham khảo chính thức: [LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api), [persistence](https://docs.langchain.com/oss/python/langgraph/persistence), [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [WebRTC](https://developers.openai.com/api/docs/guides/voice-webrtc?voice-api=realtime), [Realtime conversations](https://developers.openai.com/api/docs/guides/realtime-conversations).

Declaration: backend, UI và tests viết mới bằng Codex ngày 2026-10-31. Tái sử dụng font Urbanist/brand từ web đã có, nguồn asset ở `web/README.md` và `web/assets/SOURCES.md`. LangGraph (MIT), FastAPI (MIT), OpenAI Python SDK (Apache-2.0), uvicorn (BSD-3-Clause), httpx (BSD-3-Clause), python-dotenv (BSD-3-Clause) là dependencies; model/API là dịch vụ ngoài. H0 chưa xác nhận, không claim code viết trong giờ thi. Không copy code từ `../codex_hack`.
