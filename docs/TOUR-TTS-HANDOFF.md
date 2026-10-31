# TOUR TTS — handback cho Root / Video / Deploy

Nhận từ Tatejo, phạm vi Thái. Cwd: `.worktrees/tour-tts`, branch `feature/tour-tts`, base `37962a3d6ab198dfde7e336e9c61d697a47a0a3f`. Không push/merge/deploy, không ghi Creator/API/app/build của owner khác. H0 chưa xác minh.

## Intro thật đã sẵn sàng (ưu tiên demo)

Đúng **hai** OpenAI calls được Thái duyệt bổ sung; retries=0, timeout30, model `gpt-4o-mini-tts`, prebuilt voice `coral` (default Creator hiện hữu). Không enable global chat/Realtime; không batch thêm.

| Locale | File private ngoài Git | Script | Đo thực tế |
|---|---|---|---|
| EN | `/private/tmp/tour-tts-live-i9txpz9m/en.wav` | Welcome to the tour. Choose a stop to explore the space. | 56 chars, 4.95s, 237644 bytes |
| VI | `/private/tmp/tour-tts-live-i9txpz9m/vi.wav` | Chào mừng bạn đến với tour. Hãy chọn một điểm xem để khám phá không gian. | 73 chars, 6.15s, 295244 bytes |

WAV PCM 16-bit mono 24kHz; directory0700/file0600. Metadata: `tests/narration/evidence/live-verification.json`; private original `verification.json` cạnh WAV. Đây là actual speech qua OpenAI; chưa đánh giá chất lượng phát âm bằng người nghe. Không tự attach/publish ZInD. Deploy cần đưa đúng audio và provenance vào draft/snapshot theo owner trước demo; public snapshot hiện có không được sửa tại chỗ. Không import thành `user_uploaded`. Muốn thêm từng room: gửi trước số calls/tổng chars/script từ metadata đã verified; hai calls hiện đã dùng hết quyền live QA này.

## Đã implement

- `server/narration/api.py:install_narration` gắn vào router `/api/tours`, dùng nguyên callbacks owner/draft/revision/validate/DB; không auth mới, cookie path/Origin kế thừa.
- Script Creator duyệt rõ, SHA256 UTF-8 exact, scene existing, revision, EN/VI, prebuilt voice, request_id. Không translation/proposal tự động, không chờ geometry/3D. Whitespace đầu/cuối phải bỏ và duyệt lại, không normalize âm thầm sau hash.
- Một worker, bounded pending queue; flock fail startup khi có worker thứ hai cùng data root. SQLite jobs + global attempt/character allowance tồn tại qua restart/session; clock rollback không cấp lại allowance. Cache theo owner/text/locale/voice/model/prompt-version, TTL từ lần generate gốc, không refresh tuổi qua cache hit.
- Cancel/stale/error không attach; crash job thành error, không tự gọi lại. Provider I/O nằm ngoài SQLite write transaction. SDK retries0; timeout cấu hình ≤60s (default30). Cancellation không thể hoàn tác upstream đã nhận request/chi phí.
- PCM OpenAI → WAV header chuẩn → decoder kiểm duration/channel/rate/size; private MinIO namespace `tours/audio/{id}.wav`, object marker và membership/ownership cũ. Không silence/tone fallback. Các fixture test là tone và được ghi rõ.
- Explicit attach tăng revision, clear review; publish tạo immutable snapshot. Bilingual key `(scene_id,locale)`, tối đa20 scenes×2. Backend-owned `track.generation={provider,model,voice,locale,script_sha256}`; `audio.source=openai_generated|mixed` additive. Upload legacy shapes còn valid; track cũ không bị relabel.
- `mountNarrationPanel(container,{getManifest,onManifest,api,intervalMs?})` có script/source-copy không dịch, approval, generate/status/cancel, audio preview, attach, missing-key disabled. Returned `refresh()/pause()/destroy()`. Event `narration-preview-start` để Creator ngừng chat audio. Viewer chọn audio language riêng, thiếu đúng track thì báo thiếu; không lấy EN giả VI; chat panel pause audio.

## NEED: wiring patch, owner áp dụng sau Video

**Chưa nối production.** QA dùng hook fixture tại đúng callback install_audio và server thật; không phải bằng chứng route production đã wired. Không thêm dependency.

1. `server/tours/api.py`, ngay sau existing `verify_audio_publish = install_audio(...)`, trước `app.include_router(router)`:

```python
from server.narration.api import install_narration
app.state.narration = install_narration(
    router, db, owner, draft, check_revision, validate_doc, data_root, env,
    object_storage=object_storage,
    storage_guard=lambda: app.state.storage_limits,
)
```

Deferred storage guard cần thiết vì `install_storage` hiện chạy **sau** install tours. Không truyền `getattr(...,None)` rồi bỏ guard âm thầm. Trong `server/assistant/app.py` lifespan finally, gọi `app.state.narration.close()` trước đóng resources; dùng finally lồng để Creator/client/connection vẫn đóng nếu narration close báo lỗi. Chỉ một process/worker cho data root này.

2. `server/assistant/app.py` static `allowed`: thêm `narration-panel.js`, `narration-panel.css`. `web/build.mjs` copy hai files; `web/package.json` lint thêm `node --check narration-panel.js`. Không cần package mới. Đây là NEED; chưa sửa các files đó.

3. Creator HTML thêm stylesheet `/narration-panel.css` và `<div id="narration-panel"></div>` trong draft editor. JS import component; sau draft load/create/save/chat/audio-edit, refresh component khi revision/id đổi (không refresh mỗi keystroke). Ví dụ dùng functions/state hiện hữu:

```javascript
import {mountNarrationPanel} from './narration-panel.js';
let narrationPanel = null;
function syncNarrationPanel() {
  if (!manifest) { narrationPanel?.destroy(); narrationPanel=null; return; }
  if (narrationPanel) { narrationPanel.refresh(); return; }
  narrationPanel=mountNarrationPanel(document.querySelector('#narration-panel'), {
    api,
    getManifest: async () => {
      if (dirty || busy) throw new Error('Save draft changes before generating narration.');
      return api(`/drafts/${manifest.id}`);
    },
    onManifest: async () => {
      manifest=await api(`/drafts/${manifest.id}`); // current revision, not cached replay
      resetReview(); render();
    }
  });
}
```

Mount sau initial load; nếu hook trong render, chỉ refresh khi revision/id đổi để không xóa approval/script giữa thao tác. Nối `narration-preview-start` với hàm stop-chat-audio hiện có; khi chat voice bắt đầu, gọi `narrationPanel.pause()`. Khi draft đổi/destroy, pause. Chat/Realtime production vẫn keyless. Creator existing upload/remove narration cần giữ key `(scene_id,locale)` khi thao tác, không xóa cả hai locale theo scene_id. Giữ nhạc nền riêng, không gắn narration làm music.

4. Config patch đề xuất (owner thêm vào example/deploy; **không bật live bằng patch này**):

```dotenv
NARRATION_ENABLED=0
OPENAI_TTS_API_KEY=
OPENAI_MODEL_TTS=gpt-4o-mini-tts
NARRATION_MAX_SCRIPT_CHARS=1200
NARRATION_QUEUE_SIZE=4
NARRATION_ATTEMPTS=2
NARRATION_CHARACTERS=600
NARRATION_WINDOW_SECONDS=86400
NARRATION_CACHE_SECONDS=3600
NARRATION_TIMEOUT_SECONDS=30
```

Khi enabled1: attempts/characters/window bắt buộc positive; missing TTS key → config false/POST503, button disabled. Không fallback sang OPENAI_API_KEY ở service. `.env.local` chỉ đọc bởi standalone live QA được duyệt; Deploy dùng TTS-only secret backend env0600 và giữ `OPENAI_API_KEY` rỗng. Bật feature/budget cho các calls khác cần coordinator chốt; các defaults ở trên không cấp quyền chi tiền. Persistent window length thay đổi báo lỗi; không xóa ledger để reset. Attempt gồm cache hit, lỗi/cancel đã admission; quá queue/invalid input không trừ allowance. Attempt/character cap **không phải USD cap**, không bảo đảm exactly-once billing. Realtime streaming chat không nằm trong guard này.

5. Video/export owner: dùng **published snapshot**, chọn chính xác `audio.narration.find(n => n.scene_id===scene.id && n.locale===audioLocale)`, track URL thuộc snapshot, transcript làm subtitle, `duration_seconds` là độ dài đo thật. Missing track báo thiếu/visual-only theo policy chốt, không fallback khác locale hay mutate snapshot. Đừng filter source chỉ `user_uploaded`; hỗ trợ `openai_generated/mixed`. Chưa kiểm render MP4 vì Video lane đang sở hữu export; cần integrate + render acceptance riêng.

## Evidence / giới hạn

- Baseline trước code: `rtk proxy bash scripts/gate.sh ai --strict` PASS.
- Backend: `uv run --python 3.13 --with-requirements server/assistant/requirements.txt --with pytest --with jsonschema python -m pytest tests/narration tests/ai -q`. Tests exact SDK model/voice/instructions, real SQLite, real MinioStorage adapter + SDK fixture; no live MinIO server. Nguồn live chỉ hai Speech API calls riêng.
- Browser: `uv run --python 3.13 --with-requirements server/assistant/requirements.txt --with pytest python -m tests.narration.run_browser --live-dir /private/tmp/tour-tts-live-i9txpz9m`. Log/screenshot trong `tests/narration/evidence/`; local server/API routes thật, synthetic SDK cho flow; optional playback chỉ đọc WAV live đã sinh, không thêm calls.
- Metadata đủ cho per-scene duration/subtitle; chưa có word-level timestamp/alignment. Không script proposal/translation qua Responses (optional). Không custom speaker/voice clone. Không nhạc sinh tự động. Không container/prod integration trong task.
- SDK timeout là HTTP timeout, không phải hard wall-clock kill; stream chậm có thể kéo dài tới read timeout tiếp theo. Cancel không dừng được request đang chạy; giữ worker slot đến khi return. Có thể còn asset orphan khi cancel/crash sau object write; không public nếu không thuộc published snapshot. Cần operator reconciliation, không xóa tự động shared storage. Cache/ledger có TTL reuse nhưng chưa có retention purge.

## Nguồn / API lifecycle

Code mới Codex-assisted trong task; tái dùng models/audio/MinIO adapter/callback contracts và test fixtures của repo, không mang source ngoài. H0 unknown, không tuyên bố toàn bộ sản phẩm build trong thi.

Theo [official Speech API reference](https://developers.openai.com/api/reference/resources/audio/subresources/speech/methods/create), existing Speech API/models deprecated, shutdown **2027-01-06**; khuyến nghị `gpt-realtime-2.1-mini`/Realtime. Giữ existing configured `OPENAI_MODEL_TTS` sau abstraction theo brief, không migrate SDK/app, không fallback model. NEED decision/cost contract cho migration trước ngày shutdown. [Official TTS guide](https://developers.openai.com/api/docs/guides/text-to-speech) hỗ trợ Vietnamese/English qua input, PCM raw24kHz16-bit mono; voice optimized English nên VI cần người nghe mẫu thực tế.

Kết quả chốt 14:14 VN: AI strict gate PASS; full backend run trước hardening cuối 176 PASS; targeted narration + baseline audio sau hardening 17 PASS (7 narration +10 baseline); web6 PASS; compile/JS checks PASS. Browser fixture/keyless/existing-live-WAV playback cả3 PASS. WAV live đã play tiến thời gian trong Chromium (EN4.95s/VI6.15s), không đồng nghĩa người nghe đã duyệt phát âm. Evidence: `tests/narration/evidence/{gate-ai.log,backend.log,web-tests.log,browser.log,viewer.png,live-verification.json}`.
