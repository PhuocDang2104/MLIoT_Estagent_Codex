# Backend handoff — Estagent

Ngày rà: 2026-10-31. Baseline code đã push khi bắt đầu rà: `3887334` trên `origin/main`.
**Sẵn sàng để teammate bắt đầu phát triển backend; chưa sẵn sàng demo tour end-to-end hoặc deploy production hoàn chỉnh.**
Không cần truy cập máy Thái, repo House VR Tour hoặc herdr để chạy assistant và tests.

## 1. Quyết định và thứ tự đọc

1. `AGENTS.md`, `server/AGENTS.md`: ownership, Git và rule.
2. File này + `CONTRACTS.md`: phân biệt API thật và tour draft.
3. `USER-VIEWS.md`, `TOUR-AUDIO.md`: yêu cầu trực tiếp đã xác nhận.
4. `ASSISTANT.md`: runtime hiện có; `INTEGRATIONS.md`: dịch vụ mới chỉ là kế hoạch.
5. `Product Proposal.md` và `Business Workflow Langgraph.md` trong docs: tầm nhìn, không phải toàn bộ đã duyệt/đã code.

MVP chưa cần auth. Có hai view **Tạo tour** và **Xem tour**. Tour phải có nhạc nền + lời giới thiệu từng khu;
Viewer chỉ đọc nội dung đã duyệt và điều hướng, không sửa hồ sơ qua chat.
Thái/Tatejo là đầu mối chốt product/contract và tích hợp main; teammate lead phân task backend.
Root `Product Proposal.md`, docs proposal và `docs/PRODUCT.md` còn chứa lịch sử/đề mặc định khác nhau;
không chọn tuỳ tiện làm authority. Hai proposal còn khác về vị trí reconstruction trong LangGraph; cần chốt orchestration trước khi code phần đó.

## 2. Đã có và chưa có

| Thành phần | Trạng thái kiểm chứng |
|---|---|
| Frontend | HTML/CSS/JS tĩnh, không phải Next.js; EN/VI, motion, intake local; build bằng Node, không cần npm install |
| Assistant backend | FastAPI, LangGraph, SQLite checkpoint, một process/worker; 11 tests hiện có |
| Browser → backend | HTTP thật + graph/SQLite thật đã kiểm; extractor/network dùng fixture, không chứng minh model live |
| Text / voice OpenAI | Có code tích hợp; quyền model/quota, hiểu tiếng Việt và audio live chưa kiểm |
| Creator/Viewer đầy đủ | Mới có yêu cầu; chưa có viewer.html, draft/publish flow hoặc spatial Q&A |
| API projects/upload/jobs/tour | Chưa triển khai; bảng trong contract cũ là draft |
| PanSplat/scene/checkpoint | Chưa có `pipelines/core/`, dataset demo và artifact 3D được nghiệm thu trong repo |
| Nhạc/narration theo khu | Chưa code player/asset/schema; chưa có fixture hai khu + nhạc có quyền dùng |
| Storage/queue/Maps | Chưa có adapter Supabase/Postgres/Redis/Maps/Apify/RunPod; `.env.example` chỉ giữ tên biến |
| Deployment | Có tooling/runbook; native QA đã kiểm, chưa kiểm Docker volume/TLS/live provider |
| Strict gate | Chưa đạt: core chưa có và `fixtures/tour.schema.json` thiếu |

## 3. Clone và môi trường teammate

Cần Git, Node và Python 3.13 + uv. `requirements.txt` đã pin; không nâng version/dependency trong task khác mục đích.

```bash
git clone https://github.com/PhuocDang2104/MLIoT_Estagent_Codex.git
cd MLIoT_Estagent_Codex
git switch -c ai/be-01-contract-readiness
git config --local core.hooksPath .githooks
python3 scripts/check_commit_attribution.py --all
uv run --python 3.13 --with pytest --with-requirements server/assistant/requirements.txt \
  python -m pytest tests/ai/test_assistant.py -q
```

Nếu clone đã có hook riêng thì tích hợp checker thay vì ghi đè hooksPath. Git name/email dùng danh tính thật của teammate.
Không copy `.env.local` của Thái. Bắt đầu không có key vẫn chạy được tests và giao diện trạng thái thiếu key.
`.codex/config.toml` có MCP Silicon Labs trỏ localhost:39019 của môi trường khác; **không cần cho backend**,
không khởi động server/MCP lạ hoặc coi nó là dependency. `scripts/doctor.sh` kiểm cả CLI/GPU toàn đội;
thiếu Claude/ffmpeg/gh login không tự chứng minh assistant không chạy được.
`scripts/spawn.sh` hiện tự copy env và có thể dùng chung dependencies; không chạy mặc định cho teammate/agent chưa được giao quyền nhận secret.
Task card/report trong `tasks/` đang gitignored: card cần chia sẻ phải gửi kèm PR hoặc lưu dưới `docs/backend-tasks/` theo scope integrator giao.

## 4. Chạy local và smoke không tốn API

```bash
ASSISTANT_ORIGIN=http://127.0.0.1:5180 uv run --python 3.13 \
  --with-requirements server/assistant/requirements.txt \
  python -m uvicorn server.assistant.app:app --host 127.0.0.1 --port 5180
```

Mở `http://127.0.0.1:5180/assistant.html`. `/` của backend hiện cũng mở assistant, không phải landing.
Đừng dùng backend để phục vụ toàn bộ landing/motion: static allowlist hiện chưa bao phủ motion files.
Frontend chạy riêng: `npm --prefix web run build`, rồi `python3 -m http.server 5190 --bind 127.0.0.1 --directory web/dist`.
Assistant phải mở tại cổng backend, không mở từ static server rồi giả định `/api` đã proxy.

```bash
curl -sS -c /tmp/estagent-teammate-cookie.txt http://127.0.0.1:5180/api/assistant/state
curl -sS -b /tmp/estagent-teammate-cookie.txt \
  -H 'Origin: http://127.0.0.1:5180' -H 'Content-Type: application/json' \
  -d '{"text":"Xin chào","request_id":"teammate-smoke-01"}' \
  http://127.0.0.1:5180/api/assistant/turn
```

Chỉ thử POST trên server riêng **không có key**: kỳ vọng 503 rõ ràng, không phải câu AI giả.
Để live: tạo env riêng theo `.env.example`, kiểm key/model/account và budget trước, thêm `--env-file .env.local`.
Không dán output state có dữ liệu người dùng/cookie vào PR. Không đưa file cookie lên Git.

## 5. Source map và hành vi hiện tại

- `server/assistant/app.py`: factory `create_app`, API, Origin/body-size boundary, cookie và SQLite lifecycle.
- `server/assistant/graph.py`: `make_extractor` gọi Responses structured output; `build_graph` sở hữu policy và state.
- Graph: understand → validate → required/optional/clarify/help/review/complete → finish.
- `web/assistant.*`: chat/voice UI riêng. Voice transcript đi qua cùng graph, Realtime đọc reply; chưa là narrated tour player.
- `tests/ai/test_assistant.py`: state, correction/defer/confirm, cookie isolation, Origin, body cap, last-request duplicate, missing key và voice error sanitization.
- `tests/ai/run_local_browser.py`: kiểm HTTP/graph/SQLite thật, reload/restart/no-key; cần playwright-cli + browser, model fixture hữu hạn.
- `deploy/verify_local.py`: snapshot assistant từ HEAD, config/smoke/restart/test trong temp, key giả; không kiểm Docker/TLS.

Limits: 2.000 ký tự text, body 64 KB, API timeout 30s, SDK retries=0; text cap 1.200 tokens, voice cap 512 tokens.
Các giá trị là cấu hình hiện có, không phải ngân sách USD được duyệt. Cookie HttpOnly/SameSite strict, path `/api/assistant/`,
không đồng nghĩa tài khoản/auth. RLock chỉ trong một process; không tăng uvicorn workers để mở rộng SQLite.
Idempotency hiện chỉ nhận biết request ID cuối, chưa đảm bảo exactly-once cho jobs lâu hoặc retries sau nhiều lượt.
`address,area,bedrooms` là required-field policy tạm có thể cấu hình, chưa được chốt thành sản phẩm.
Không có dedicated health endpoint, OpenAPI/docs UI bị tắt; contract/source/tests là tài liệu API hiện tại.

## 6. Backlog đề xuất cho teammate lead

| Thứ tự | Deliverable | Acceptance và dependency |
|---|---|---|
| BE-01 | Đề xuất contract tích hợp Creator/Viewer | Route/payload/error, property ID ↔ session, draft/published snapshot, job lifecycle, audio/checkpoint; gửi integrator chốt trước code liên lane |
| BE-02 | Schema + fixture với integrator | Fixture tour tối thiểu hai khu, status/error, nguồn dữ kiện và audio metadata; schema kiểm được fixture, không fabricate reconstruction |
| BE-03 | Projects/upload/job orchestration | Validate input, tạo/đọc job, progress/error/idempotency/cancel policy đã chốt; worker adapter fixture khi core chưa có |
| BE-04 | Nối Creator intake vào property draft | Không ghi chéo phiên, xác nhận intake tách publish tour; FE gọi backend thật, test reload/restart/error |
| BE-05 | Tour builder + audio artifacts | Scene observations/metadata → lời có nguồn → narration/timing + nhạc có rights; live chỉ trong budget đã giao |
| BE-06 | Viewer context/Q&A/tools | Đọc published snapshot, room/camera context, navigation action allowlist; câu hỏi người xem không làm đổi source metadata |
| BE-07 | Storage/deploy integration | Estagent storage riêng, namespace riêng, proxy/cookie/Origin/TLS; không migration hoặc động vào stack khác khi chưa được giao |

Mỗi card 20–45 phút, có Paths + Acceptance + nguồn + API budget/mode. Không nhận tất cả như một task lớn.
BE-01 và kiểm môi trường làm được ngay, không chờ key/GPU. BE-02 trở đi cần contract thống nhất với integrator/FE/core.
Blender/free-roam/video export/market data không tự thêm vào P0 từ proposal.

## 7. Bàn giao agent cho teammate — prompt dùng ngay

```text
Bạn là agent backend của Estagent. Đọc AGENTS.md, server/AGENTS.md,
docs/BACKEND-HANDOFF.md và docs/CONTRACTS.md, rồi task card được giao.
Không yêu cầu file Tatejo hoặc herdr trên máy Thái. Scope theo Paths của card.
Task đầu tiên: BE-01, đọc source thật và đề xuất contract, chưa code schema/API tour.
Paths ghi: docs/backend-tasks/BE-01-PROPOSAL.md. Source đọc: server/assistant/,
web/assistant.*, docs/USER-VIEWS.md, docs/TOUR-AUDIO.md và contract/handback liên quan.
Acceptance: kiểm đúng endpoints đang có, liệt kê payload/status/error và missing pieces;
đề xuất mapping Creator/Viewer, job/core/audio và các câu hỏi cần integrator quyết.
Không gọi API tính phí, không tạo auth, không sửa runtime/dependency/root/main.
Không thêm attribution Claude/Anthropic; vẫn khai nguồn và AI hỗ trợ trung thực.
Commit đúng file trên nhánh cá nhân nếu dev đã giao quyền commit; không push main.
Report: STATUS, CHANGED, EVIDENCE, NEED, CONTRACT_CHANGE, NOTES, base SHA.
```

## 8. Kiểm trước PR / hạn chế còn mở

Chạy backend tests, `bash scripts/gate.sh ai --strict` và attribution checker. Strict hiện FAIL vì thiếu contract,
không giảm strict/xóa test để báo xanh; PR nêu tests nào pass và blocker do baseline nào.
Frontend có 6 tests và backend có 11; mock/live phải ghi riêng. Khi có contract mới, schema + fixture cùng PR được integrator review.
Commit source không chứa env/DB/upload. Mỗi clone bật hook; chỉ push nhánh task được giao, integrator merge.

Ngoài backend còn thiếu: dataset/GPU/model license cho core, nhạc có license/audio thực, quyền hero reference,
H0/baseline thi, mapping hai view, hostname/TLS/proxy cuối và model/budget live. Không biến các mục này thành giả định đã chốt.
Runbook Vercel/VM còn phản ánh thời điểm khảo sát; kiểm với lane Deploy trước khi làm hạ tầng, không tự deploy theo tài liệu cũ.

## 9. Kết quả audit bàn giao

Trên baseline `3887334`, chạy lại `bash scripts/gate.sh all --strict`: web lint/test/build PASS,
AI compile/pytest PASS; core SKIP, contract SKIP; exit 1 `GATE FAIL (strict: còn SKIP)`.
Đây là blocker baseline, không phải lỗi cài môi trường backend của teammate.
Attribution checker, diff whitespace và các link local trong bộ bàn giao đều PASS.
Đợt audit chỉ sửa docs/rule, không thay API/runtime/schema/dependency và không gửi paid request.
