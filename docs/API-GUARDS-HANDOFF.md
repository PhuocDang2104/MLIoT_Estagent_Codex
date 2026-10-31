# W2 API guards — handoff cho integrator

Nhận từ Tatejo, card `docs/work-items/W2-API-GUARDS.md`.
CWD: `/Users/anhoaithai/Documents/AHT/1. PROJECTS/CodexHackathon/.worktrees/live-api-guards`.
Branch: `feature/live-api-guards`; base: `a28e43177533eee4279d97f21c1e408128e5bff6`.
Chỉ sửa `server/limits.py`, `tests/ai/test_api_limits.py`, tài liệu này. Không auth,
không đụng Audio lane, không dùng key/paid API/production và không thêm dependency.

## Kết quả và semantics

`install_limits(app, env)` cài pure ASGI middleware; cần integrator wiring ở factory.
Hiện **chưa được cài vào app chính** trong nhánh này. Khi được bật:

- Chung một nhóm AI cho POST `/api/assistant/turn`, `/api/assistant/voice`,
  `/api/tours/drafts/{id}/chat`, `/api/tours/published/{id}/chat`.
- Nhóm upload riêng cho POST `/api/tours/assets`, có burst/concurrency riêng.
- Giới hạn burst và allowance AI theo hai fixed window, bắt đầu từ request được nhận
  đầu tiên. Không phải sliding window: có thể nhận hết hạn mức ngay trước và sau ranh giới.
  Window mới chỉ bắt đầu khi có admission sau expiry; không trừ allowance theo model trả lời.
- SQLite riêng lưu ba dòng window (`ai_burst`, `ai_allowance`, `upload_burst`) và một
  clock highwater. Atomic check + increment trong một `BEGIN IMMEDIATE`; transaction đã
  commit/close trước khi chạy endpoint. Thời gian chờ SQLite lock tối đa 100 ms/lần;
  lỗi/lock storage trả 503 rõ ràng, không gọi downstream mà bỏ qua limiter.
- Restart app dùng cùng DB giữ count và thời điểm window. Clock lùi dùng highwater đã lưu,
  không cấp quota mới. Cap thay đổi vẫn giữ used; đổi duration của window đã dùng trên cùng
  DB bị từ chối cấu hình, không âm thầm reset. Không xoá/đổi DB để làm mới allowance.
- Một **attempt** là request được middleware nhận trước route validation/model. HTTP
  4xx/5xx, thiếu key, request replay/idempotency hit và cancellation vẫn tiêu attempt;
  không biết provider có tính phí hay không nên không refund. Request bị chính guard chặn
  không tiêu attempt. Trailing-slash redirect có thể tiêu thêm attempt khi client đi theo redirect;
  dùng URL canonical trong frontend.
- HTTP 429 có `error` dạng chuỗi tương thích UI hiện tại, `code`, `retry_after` và header
  `Retry-After`. Codes: `rate_limited`, `attempt_allowance_exhausted`, `concurrency_limited`.
  Concurrency retry 1 giây là gợi ý, không đảm bảo slot sẽ trống. Storage lỗi: HTTP 503,
  code `limits_unavailable`, không lộ lỗi SQLite/path.
- Semaphore được release trong `finally` khi app kết thúc/lỗi/cancel; giữ slot cả khi
  đang gửi streaming response. Không giữ DB transaction trong thời gian đó.
- GET/session/state/assets đọc không bị trừ quota. Body không được đọc bởi guard. Body cap,
  Origin check, cookie và các response thành công/lỗi của endpoint giữ nguyên khi chưa hết quota.
- Không đọc IP, cookie, X-Forwarded-For hay X-Real-IP để chia quota. Ledger chỉ có tên bucket
  cố định, thời gian và counter; không chứa key, token, tin nhắn, ID tour hay URL request.

## Config: explicit opt-in, không tự bật live

Không đặt `API_LIMITS_ENABLED` tương đương `0` **chỉ cho môi trường keyless**. Khi key
OpenAI không rỗng mà limiter chưa bật, installer báo lỗi cấu hình, không chạy unguarded.
`API_LIMITS_ENABLED` chỉ nhận `0`/`1`. Khi bật, mọi biến AI và đường dẫn DB bên dưới bắt buộc;
thiếu/rỗng/âm/0/sai kiểu phải lỗi nêu tên biến. Installer không log giá trị env.

Đây là **đề xuất cấu hình nhỏ để integrator duyệt**, không phải budget USD hay quyền gọi live:

```dotenv
API_LIMITS_ENABLED=1
API_LIMITS_DB=/data/api-limits.sqlite
API_LIMITS_AI_REQUESTS=6
API_LIMITS_AI_WINDOW_SECONDS=60
API_LIMITS_AI_CONCURRENCY=1
API_LIMITS_AI_ATTEMPTS=50
API_LIMITS_AI_ATTEMPT_WINDOW_SECONDS=3600
# Upload có default hợp lệ nếu bỏ ba biến này:
API_LIMITS_UPLOAD_REQUESTS=6
API_LIMITS_UPLOAD_WINDOW_SECONDS=60
API_LIMITS_UPLOAD_CONCURRENCY=1
```

Mỗi số nguyên dương tối đa 9 chữ số; window allowance phải >= window burst.
`API_LIMITS_DB` phải là đường dẫn absolute, file riêng, không symlink trực tiếp, không trùng
ASSISTANT_DB/tours.sqlite. DB đã có bảng của ứng dụng khác bị từ chối; file ledger đặt mode 0600.
Giữ trên volume bền vững. Không dùng `/tmp` ở deployment. Thư mục cha phải writable bởi app.
Upload cap không thay 12 MiB/image cap hiện tại, proxy body cap hoặc quota dung lượng lưu trữ.

## NEED — patch wiring chính xác (chưa áp dụng)

Ở base này không có `server/tours/app.py`; factory thật nằm tại `server/assistant/app.py`.
Integrator thêm import và cài **sau các middleware khác, trước return app**, để guard chạy
trước body buffering/model; không cần sửa `server/tours/api.py`:

```diff
--- a/server/assistant/app.py
+++ b/server/assistant/app.py
@@
 from .graph import build_graph, make_extractor, LABELS, QUESTIONS
+from server.limits import install_limits
@@
     app.mount('/assets',StaticFiles(directory=WEB/'assets'),name='assets')
+    install_limits(app, env)
     return app
```

`deploy/compose.yaml`, thêm dưới `services.assistant.environment` (DB dùng volume `/data` đã có):

```yaml
      API_LIMITS_ENABLED: ${API_LIMITS_ENABLED:-0}
      API_LIMITS_DB: /data/api-limits.sqlite
      API_LIMITS_AI_REQUESTS: ${API_LIMITS_AI_REQUESTS:-}
      API_LIMITS_AI_WINDOW_SECONDS: ${API_LIMITS_AI_WINDOW_SECONDS:-}
      API_LIMITS_AI_CONCURRENCY: ${API_LIMITS_AI_CONCURRENCY:-}
      API_LIMITS_AI_ATTEMPTS: ${API_LIMITS_AI_ATTEMPTS:-}
      API_LIMITS_AI_ATTEMPT_WINDOW_SECONDS: ${API_LIMITS_AI_ATTEMPT_WINDOW_SECONDS:-}
      API_LIMITS_UPLOAD_REQUESTS: ${API_LIMITS_UPLOAD_REQUESTS:-6}
      API_LIMITS_UPLOAD_WINDOW_SECONDS: ${API_LIMITS_UPLOAD_WINDOW_SECONDS:-60}
      API_LIMITS_UPLOAD_CONCURRENCY: ${API_LIMITS_UPLOAD_CONCURRENCY:-1}
```

Integrator thêm các tên biến vào `.env.example`/`deploy/.env.example`, để flag `0` cho keyless
compatibility, ghi rõ cấu hình live bắt buộc theo bảng trên. Không đưa key vào ví dụ.
`deploy/entrypoint.py --check-config` hiện chỉ kiểm cấu hình cũ; đề xuất bổ sung sau kiểm
ASSISTANT_DB để kiểm cả guards mà không tạo OpenAI client hoặc gọi provider:

```python
from fastapi import FastAPI
from server.limits import install_limits
install_limits(FastAPI(), os.environ)
```

Đoạn preflight này sẽ tạo/kiểm ledger nhưng không tiêu attempt. Installer gọi ở factory vẫn là
nguồn kiểm bắt buộc, kể cả chạy uvicorn trực tiếp không qua entrypoint. Giữ `--workers 1`,
`--no-proxy-headers`, `--no-access-log` đã có. Tests fixture có fake key cần truyền config
guards đầy đủ sau wiring; không tắt limiter chỉ để làm xanh tests live-key diagnostics.

## Giới hạn trước live, rollout và rollback

- **Không phải USD/token cap.** Một request có thể nhiều token/call; số request bị tính ở
  middleware không tương đương billed requests. SDK retries/model/tool limits vẫn phải kiểm riêng.
- Semaphore là **một app instance, một process/worker**, phù hợp deployment hiện tại. SQLite
  reservation atomic giữa các connection, nhưng không claim concurrency global nhiều worker/
  replicas. Khi restart cần graceful drain; không chạy old/new replica đồng thời để lách slot cap.
- ASGI cancel release slot không bảo đảm provider hoặc thread sync đã dừng xử lý/tính phí.
  Giữ timeout của upstream; cần cancellation thực sự hoặc provider budget nếu muốn bound work
  ngoài vòng đời request. Không claim chỉ thêm middleware là đủ khóa mọi chi phí.
- **Realtime chỉ chặn SDP setup.** Sau SDP, WebRTC nối browser–OpenAI trực tiếp; HTTP slot đã
  trả lại. Guard không giới hạn stream duration, số stream còn sống hoặc tiền audio. Timer UI
  5 phút có thể bị bỏ qua. NEED trước live voice: cơ chế server quản lý/đóng session, số session
  đang sống và thời lượng, cộng hạn mức provider phù hợp; chưa có các phần này trong card.
- No-auth + global quota có thể bị một client dùng hết; không có công bằng theo user. Origin
  không thay auth. Guard không bao phủ GET flood hay toàn bộ các write không gọi AI; edge cần
  giới hạn traffic/body phù hợp. Không bật thêm auth hoặc suy container IP là người dùng.
- Rollout: tích hợp patch → chạy tests no-key/fixtures và gate → xác minh volume persist và
  rejection sau restart → duyệt riêng input/provider/budget cho live text. Không bật live voice
  dựa riêng vào các guard này. Lần triển khai này chưa làm bất kỳ bước production nào.
- Rollback: trước khi bỏ wiring/disable guard, bỏ key và trở lại keyless preview theo quy trình
  integrator. Giữ ledger/volume để tránh reset allowance khi roll forward. Không rollback thành
  app có key nhưng không guard; không đổi window/DB hoặc xoá dữ liệu production trong card này.

## Kiểm chứng và nguồn

Baseline reproduce: endpoint fixture không guard nhận ba POST liên tiếp đều HTTP 200.
QA sau thay đổi dùng FastAPI/ASGI thật, SQLite thật trong thư mục tạm và clock tiêm vào; không
mock reservation/transaction. Chỉ test lỗi storage chủ động inject OperationalError; model
assistant là fixture. Không cần mạng/credential hoặc mở socket public.

- `python3 -m pytest tests/ai -q`: **47 passed** (27 guard mới + 20 baseline), 1 cảnh báo
  deprecation từ dependency LangGraph; chạy trong worktree này, 2026-10-31.
- `bash scripts/gate.sh ai --strict`: **GATE OK (ai)**, compile/pytest/tour contract đều PASS.
  Không chạy hoặc tuyên bố core đã xanh; core SKIP là baseline integrator đã thông báo.
- `git diff --cached --check`: kiểm trước commit; chỉ stage ba file của card.
- Tests có burst chung qua bốn endpoint, upload riêng, Retry-After, concurrency bình thường/
  exception/stream cancel, allowance qua app recreation, boundary/clock lùi, atomic race hai app,
  config thiếu/sai, dedicated storage, không lưu dữ liệu request và semantics assistant thật.
- Không thay tour schema, không migrate checkpoint/tour DB; chỉ tạo ledger riêng sau explicit opt-in.
- Code/tests/docs viết với Codex ngày 2026-10-31 dựa trên card, source hiện có và stdlib SQLite/
  threading + FastAPI/Starlette đã cài. Không copy code dự án tham khảo, không thêm dependency.
  H0 chưa xác nhận; không claim phần này viết trong giờ thi.
