# Chat trong tour — bàn giao F / Tatejo

Direct Thái request: chatbot ngay trong trang tour để khách hỏi thêm thông tin căn nhà. User chọn dùng API tour hiện có; không auth. Cwd `.worktrees/house-chat`, branch `feature/house-chat`, base `4ade918aa3d9afa5b81eeb34e8715357af4030f6`. Chỉ local; F vẫn là người ghi production. Không push/deploy hoặc thay env production.

## Đã làm

- Nút Hỏi về căn nhà trên house tour; EN/VI, scene đang xem, hỏi rõ khi thông tin mơ hồ, điều hướng đến scene hợp lệ khi được yêu cầu. Không sửa/publish tour từ chat.
- Reuse `POST /api/tours/published/{id}/chat`, Chat/TourReply và Manifest hiện có. Snapshot từ description EN/VI đã duyệt của 15 rooms/16 markers; không thêm suy đoán diện tích/giá/vật liệu/địa lý. Description public là nguồn, không nạp dữ liệu draft hay hội thoại owner khác.
- LangGraph trả lời → validate read-only. SQLite giữ hội thoại theo cookie owner + snapshot, bounded model history 6 lượt; replay cùng request trả kết quả cũ, payload khác/stale revision báo 409. Failed/interrupted paid attempt không tự chạy lại cùng ID.
- Voice theo lượt: browser ghi tối đa20s mono16k PCM WAV, STT để người dùng kiểm rồi bấm gửi; Nghe dùng đúng câu trả lời đã lưu của phiên. Giọng AI coral, không clone; TTS PCM24k/16bit mono bọc WAV, validate trước lưu private.
- Chat/focus dừng guide/auto-next. Khi tour hoặc audio khác phát, chat audio dừng; response TTS đã bị thay thế không tự phát. Locale/pagehide/hidden tab dừng voice.
- Key chuyên biệt `OPENAI_TOUR_API_KEY`; không cần bật `OPENAI_API_KEY` hay Realtime. Concurrency1, OS lock per data root, durable attempt ledger; retries0, timeout30s. Giữ legacy global key/interpreter consumers khi feature flag tắt.

## NEED: F tích hợp và cấu hình (không tự bật production)

Các hook đã có trong branch để review/cherry-pick: `server/tours/api.py`, `server/assistant/app.py`, `server/demos/__init__.py` static allowlist; `web/demos/house.html` thêm CSS/module; `web/viewer.js` đọc capability Viewer riêng (một dòng). Không đổi house.js, renderer hay MinIO catalog. `web/build.mjs` đã copy toàn bộ demos nên không cần dependency/build patch.

Seed immutable public snapshot vào thư mục operator quản lý; source local:
`/private/tmp/house-chat-qa/snapshots/33e7d1e17c6ce7f87d9157906a9a439e.json`.
SHA256 snapshot: `9cc6071e878f12d381248d2e14c362aea1570dbda844de146c9ff2badf1c0f6a`. Đây là thông tin đã public, không chứa key/cookie. Snapshot pin lúc startup; giữ file cũ khi seed bản mới. ID SHA từ sorted `[capture_id,room_id,locale,description]`; browser và backend dùng cùng cách. Nếu guide được cập nhật, seed snapshot mới trước khi restart. Module `server.demo_chat.snapshots.build_snapshot(house,guide)` tạo bằng Manifest validator hiện có.

Config patch đề xuất, **các cap4/1/1 bên dưới chỉ tái hiện QA, không phải budget production đã duyệt**:

```dotenv
OPENAI_API_KEY=
OPENAI_TOUR_API_KEY=<backend-only secret; F provisions in env0600>
TOUR_CHAT_ENABLED=1
TOUR_PUBLIC_SNAPSHOTS_DIR=<operator snapshot directory>
TOUR_CHAT_TEXT_ATTEMPTS=4
TOUR_CHAT_STT_ATTEMPTS=1
TOUR_CHAT_TTS_ATTEMPTS=1
OPENAI_MODEL_TEXT=gpt-6.1-sol
OPENAI_MODEL_STT=gpt-4o-mini-transcribe
OPENAI_MODEL_TTS=gpt-4o-mini-tts
```

`TOUR_CHAT_ENABLED=0` default. Missing key → session configured=false, disabled Send/Mic and 503 on uncached call. Enabled feature requires explicit positive caps; malformed config fails startup. Existing `ASSISTANT_ORIGIN` must match exact public origin. Keep single application worker per data root as required by existing narration worker. Backup/persist `TOUR_DATA_DIR` including tours.sqlite and visitor-chat databases/cache. Do not reset live ledger to regain quota.

## CONTRACT_CHANGE: additive helpers under existing tours boundary

Main Chat/TourReply/Manifest shapes unchanged; no `/api/demos/*/chat` namespace.

- Session adds optional `viewer_configured` / `voice_configured` booleans. Existing `configured` keeps its Creator meaning; dedicated visitor key never enables Creator chat. Generic published-tour Viewer reads viewer_configured with legacy fallback; house panel does likewise.
- `GET /api/tours/published/{id}/messages`: latest50 own-session turns `{text,locale,request_id,reply,scene_id,source}`. No Creator messages.
- `POST .../{id}/transcribe`: raw WAV body≤640044 bytes, headers `X-Request-ID`, `X-Audio-Locale=en|vi`; returns `{text}`. Validates PCM duration/rate/channel before provider call.
- `POST .../{id}/speech`: `X-Request-ID` references an existing chat answer in the same cookie/session/snapshot; returns `audio/wav`, private/no-store. No arbitrary text-to-speech endpoint.
- Both writes inherit exact Origin and `/api/tours/` cookie. No trusted X-Forwarded-For identities, no login or new role security.

F/integrator owns adding these additive helpers/config to central CONTRACTS/.env.example; those shared root files were not edited.

## Evidence

All private QA artifacts: `/private/tmp/house-chat-qa/`.

- Baseline `scripts/gate.sh ai --strict`: PASS (`/private/tmp/house-chat-baseline.log`).
- Final AI and web strict gates: `gate-ai-final.log`, `gate-web.log`.
- Deterministic tests: 30 passed; `tests/ai/test_house_chat.py`, existing narration/audio tests; `targeted-tests.log`.
- Browser: `tests/ai/run_house_chat_browser.py` with real local HTTP/LangGraph/SQLite and production chat/bootstrap/house.js. Room-control DOM is a fixture, **not** full WebGL/MinIO/prod render. Mocked model/STT; generated tone WAV explicitly fixture. `browser/browser.log`, `browser/keyless.log`, `browser/browser.png`: current room, reload history, requested garage navigation, record/transcript review, voice playback, real guide controller pause, mobile layout, keyless UI.
- Live user-authorized allowance used exactly **4 text +1 STT +1 TTS**, no retries. Responses in `live-results.json`; models gpt-6.1-sol / gpt-4o-mini-transcribe / gpt-4o-mini-tts. EN greeting; VI current-room visible features; unknown floor area/rent explicitly unavailable; garage scene matches existing marker.
- STT recognized existing real EN intro accurately. TTS: `chat-reply-en.wav`, 2.95s, PCM16 mono24k, voice coral; SHA256 `57ad5318b8e978eb315fe28f0773065c7f2e796ed716e08b716bd41278805972`. Browser `live-playback.log` verifies actual file decoded and played. No claim of human listening/VI voice QA in this new budget.

Reproduce deterministic browser (no secrets, no paid calls):

```sh
uv run --python 3.13 --with pytest --with jsonschema --with-requirements server/assistant/requirements.txt python -m tests.ai.run_house_chat_browser --house /private/tmp/estagent-house-audit/viewer/public/house/manifest.json --guide /private/tmp/house-chat-public-guide.json --output /private/tmp/house-chat-qa/browser --live-wav /private/tmp/house-chat-qa/chat-reply-en.wav
```

When running gates concurrently with another local app, give the gate's import-time default app its own ASSISTANT_DB. Initial gate collision reproduced existing narration process lock; no locks or checks were weakened.

## Limits / source declaration

Counts are per rolling fixed24h window anchored at first admission, global across sessions and persisted restart; **not a token/USD cap**. SDK timeout30s is a request/network timeout, not a guarantee of provider cancellation/billing. Failed request consumes allowance; no exactly-once billing claim. Realtime streaming is not used or bounded by this module. Anonymous sessions are cookie isolation, not authentication; one visitor can consume the shared allowance. Audio cache is private per answer/model/locale; operator retention/storage policy still applies.

Speech API/default gpt-4o-mini-tts lifecycle: earlier official reference marks deprecated/shutdown2027-01-06 and recommends Realtime successor. Reused existing Speech abstraction; no automatic model/SDK migration or fallback. F needs separate decision before migration.

Source: pre-existing FastAPI/LangGraph/SQLite/OpenAI SDK2.54.0, `TourReply`/Chat/Manifest, cookie/Origin/persistence, limit ledger/file lock and narration PCM adapter; public approved ZInD guide descriptions. New Codex-assisted provider/graph/snapshot adapter, bounded service, chat panel, hooks/tests. Official OpenAI structured-outputs and speech-to-text docs checked; prior TTS official docs reused. No additional runtime dependency or panorama/audio assets committed. H0 unverified: no claim of in-contest authorship.
