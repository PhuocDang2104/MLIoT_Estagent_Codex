# Bàn giao Chatbot — vòng 1 local

- Nhận từ: Tatejo, brief vòng 1, lane Chatbot `w6E:p1` theo `docs/LANE-DISPATCH.md`.
- CWD: `/Users/anhoaithai/Documents/AHT/1. PROJECTS/CodexHackathon`.
- Commit nền lúc nhận và lúc kiểm: `9a1e40f89e2afa1a5e0ec2671a21187ff4efe723`.
- Không commit/push/stash; checkout chung có thay đổi của các lane khác.
- Ngày kiểm: 2026-10-31. Phạm vi: local, một worker, không auth; model fixture, không paid API.

## Đã làm

1. Tái hiện key chỉ chứa khoảng trắng vẫn trả `configured: true`; sửa `server/assistant/app.py:33` để chuẩn hóa key trống. Không thay tên config, endpoint hay schema.
2. Mở rộng kiểm thiếu key cho absent/empty/whitespace, cả text và voice trả 503 rõ, profile/history không đổi.
3. Thêm harness browser gọi HTTP server thật, LangGraph thật và SQLite thật. Chỉ model extractor dùng bảng phản hồi hữu hạn; không giả lập API ở browser. Test không nạp `.env.local` hoặc key/tracing từ shell, không gọi OpenAI.
4. Kiểm submit nhiều dữ kiện, bỏ qua optional, xác nhận, sửa, reload và restart process backend; dữ liệu vẫn được khôi phục qua cookie và SQLite. Xóa localStorage/sessionStorage trước reload để không nhầm với lưu trong browser.
5. Kiểm model fixture từ chối câu ngoài bảng: HTTP 502 hiển thị lỗi, giữ hồ sơ/lịch sử đã nhận và giữ câu vừa gửi để thử lại.
6. Chạy backend lại không có key trên cùng SQLite: đọc được hồ sơ, nút gửi/micro disabled, POST text/voice trả 503. Không thêm auth, email hoặc integration.
7. Cập nhật `docs/ASSISTANT.md`: bỏ yêu cầu thêm auth trước deploy, ghi cách tái chạy và giới hạn mock/live.

## Bằng chứng

| Lệnh / phép kiểm | Kết quả | Artifact |
| --- | --- | --- |
| `python3 -m pytest tests/ai/test_assistant.py -q` trước sửa | 9 passed | `baseline-tests.log` |
| `python3 -m pytest tests/ai/test_assistant.py -q` sau sửa | 11 passed; 1 cảnh báo dependency LangGraph | `backend-tests.log` |
| `python3 tests/ai/run_local_browser.py` | 3 pha PASS: flow, restart backend, missing-key | `local-browser.log` |
| Browser desktop 1440, mobile 390/320 | Không có JS pageerror ở flow; không tràn ngang mobile; đã xem ảnh desktop/mobile | `local-desktop.png`, `local-mobile-320.png` |
| Browser sau restart / không key | Hồ sơ 90 m² còn hiển thị | `local-after-restart.png`, `local-no-key.png` |
| `node --check web/assistant.js` | PASS | stdout của lượt kiểm |
| `bash scripts/gate.sh ai --strict` | Compile + pytest PASS; strict FAIL do contract SKIP | `ai-gate.log` |
| `git diff --check -- server/assistant tests/ai web/assistant.html web/assistant.js web/assistant.css docs/ASSISTANT.md docs/INTEGRATIONS.md .env.example` | PASS | stdout của lượt kiểm |

Artifact trong bảng tính tương đối từ `tests/ai/evidence/`. Log server chỉ có cảnh báo dependency: `local-server.log`. Browser có HTTP 502/503 cố ý kiểm đường lỗi; chúng không phải lỗi ngoài dự kiến.

Lần chạy đầu harness gặp `ReferenceError: URL is not defined` trong sandbox của Playwright CLI. Đây là lỗi script kiểm, không phải app; đã đổi kiểm origin bằng tiền tố `${base}/` và chạy lại toàn bộ ba pha thành công. Sandbox OS chặn bind localhost ở lần thử đầu; chạy kiểm bằng quyền local browser/server được runtime cấp, không thay host hay gọi provider.

## Còn thiếu / NEED

- Gate strict chưa đạt vì thiếu `fixtures/tour.schema.json`. File thuộc integrator, ngoài Paths của lane; không tự bịa schema để làm gate xanh. Integrator cần chốt contract rồi thêm schema/fixture tương ứng. Không có patch schema đề xuất vì chưa có contract cuối được duyệt.
- Chưa kiểm model hiểu tiếng Việt hoặc âm thanh OpenAI live. Có key không cấp budget; cần input/host/budget cụ thể trước paid smoke. Fixture không chứng minh chất lượng model.
- Không cần wiring mới cho nghiệm thu local: backend đã phục vụ `/assistant.html` và `/api/assistant/*` cùng origin. Deployment/proxy và nối intake cũ để lane phụ trách; vòng này không sửa build/package/root hoặc trang intake.
- Policy bắt buộc `address,area,bedrooms` vẫn là cấu hình nháp hiện có, không được bài test này biến thành quyết định product.

## File chính và khai báo nguồn

- Runtime: `server/assistant/app.py` (một dòng chuẩn hóa key).
- Tests: `tests/ai/test_assistant.py`, `tests/ai/local_fixture_server.py`, `tests/ai/run_local_browser.py`, `tests/ai/local_browser_{flow,restart,no_key}.js`.
- Runbook: `docs/ASSISTANT.md`.
- Test harness/fixture và sửa code được viết với Codex ngày 2026-10-31; dùng API ứng dụng/schema đã có, không copy source tham khảo, không thêm dependency. Screenshot lấy từ UI hiện có và dữ liệu mẫu của fixture. H0 chưa xác nhận; không claim code được viết trong giờ thi.

## Bổ sung handback — backlog tour audio

Đã đọc `docs/TOUR-AUDIO.md` sau Acceptance vòng 1. Yêu cầu mỗi tour có nhạc nền và giọng giới thiệu từng khu đã được ghi nhận; chưa triển khai audio trong card assistant local.

- AI nhận script theo room/checkpoint, tham chiếu nguồn thông tin được duyệt, audio EN/VI và duration/timing đo từ asset thực. Fixture phải ghi rõ; không suy timing từ số từ rồi coi là timing thật.
- Frontend nhận player/controls, ducking, đồng bộ room-camera-phụ đề và quyền phát duy nhất giữa tour với chatbot. Khi mở hội thoại, dừng lời tour; chỉ tiếp tục tour khi người dùng chọn tiếp tục, không tự phát lại sau khi chatbot xong.
- NEED cho card audio: chốt schema/fixture với ít nhất hai khu; giao nguồn metadata đã duyệt và nhạc có quyền phân phối; xác định nguồn voice/fixture hoặc provider, input và budget TTS. Chốt giao diện phối hợp player–chatbot với owner Frontend trước khi nối vào `web/assistant.*`.
- CONTRACT_CHANGE đề xuất, chưa áp dụng: giữ tương thích `narration.lines[].room`; bổ sung tham chiếu asset narration theo room/checkpoint và ngôn ngữ, timing/phụ đề theo cùng mốc thời gian đã định nghĩa, tham chiếu nguồn cho script; bổ sung track nhạc nền và credits/license. Tatejo chốt tên trường, mốc thời gian, version và fixture trước khi giao code.
- Acceptance card sau cần phát audio asset thật trong browser và kiểm chuyển khu/tua/Pause/Resume/EN-VI/lỗi tải/không chồng giọng; kết quả assistant vòng 1 không chứng minh các tiêu chí audio này.

STATUS: PARTIAL
CHANGED: server/assistant/app.py; tests/ai/; docs/ASSISTANT.md
EVIDENCE: 11 backend tests PASS; browser real HTTP/LangGraph/SQLite 3 pha PASS; ai strict FAIL do thiếu tour.schema.json
NEED: integrator chốt schema fixture; card audio cần nguồn/rights/budget và giao diện player–chatbot
CONTRACT_CHANGE: đề xuất additive audio theo room/ngôn ngữ, timing/nguồn và nhạc/credits; chưa áp dụng
NOTES: Local flow đã kiểm; model fixture; audio mới là backlog, không paid API/auth/commit/push/stash.
