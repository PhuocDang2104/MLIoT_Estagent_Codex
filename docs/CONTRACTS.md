# CONTRACTS — giao diện giữa 3 lane

## Studio runtime additive — 2026-10-31

Authority: Thai explicitly approved runtime framework and main integration;
reconstruction/MP4 deferred. Existing tour/assistant/published schemas unchanged.
Generation adds `revision,parent_id`; Review optionally accepts revision (new UI
sends it). `GET /api/studio/health` checks dispatcher/store, no paid call.
`POST /api/studio/generations/{id}/edits` accepts request_id/revision/text;
GET lists owner-scoped proposals. `POST .../edits/{edit_id}/apply` accepts
request_id/revision, returns new generation id. Owner/revision/ID/evidence checks,
explicit confirmation, durable dedup/outbox and immutable published snapshots
are enforced by backend. Geometry HTTP v1: [STUDIO-RUNTIME.md](STUDIO-RUNTIME.md).

## Additive: AI Generation Studio

Đọc `CREATOR-STUDIO.md` cho luồng LangGraph dài của các dự án Studio đã lưu tại `/business/projects/{id}/generate`. Cửa vào `/business/create` hiện phục vụ luồng tour ảnh bên dưới.
Luồng này dùng `/api/studio/*`, `/api/studio-tours/*` và cookie/storage riêng;
giữ nguyên `/api/tours/*`, schema Manifest và các trang Creator/Viewer hiện có.
Schema mới: `fixtures/studio-tour.schema.json`, fixture tổng hợp
`fixtures/studio-example/studio-tour.json`; gate kiểm cả hai bộ schema.
Studio có checkpoint persistence, SSE replay, spatial/final interrupt, worker
adapter, narration/TTS và immutable publish. Không có worker thì chờ integration
và chặn publish. Không giả dựng 3D hoặc tự suy panorama chỉ từ tỷ lệ ảnh.
Các endpoint, payload, giới hạn và điểm nối worker ghi trong card trên.

House-modeling integration (user-authorized): see `HOUSE-MODELING-AGENT.md`.
Generation responses add private `modeling_plan` and `plan_attempts`. Spatial
review additionally accepts `decision=revise`, `clarification` (<=3000 chars),
and `accept_approximate`. Final review still accepts only approve/reject.
Published v1 anchor fields optionally add `dollhouse_visible`, `heading` and
`accuracy`; optional model `metadata` records units, axes, scale, builder and plan
hash. Defaults preserve older packages/worker adapters. Updated v1 JSON Schema
and synthetic fixture are checked together. The internal HousePlan is not a
public tour contract; it is validated before execution and remains private.

> **Trạng thái: v0 nháp** (rút từ `../codex_hack`). Dev 1 sửa theo đề thật rồi **freeze v1 trước H0:45**.
> Chủ file: Dev 1. Sau freeze chỉ được thêm field (additive), bump `version`, sửa `fixtures/` trong cùng commit.
> Lane nào cũng code dựa trên fixture trong `fixtures/`, không chờ lane khác.

## Trạng thái bàn giao 2026-10-31 — đọc trước khi triển khai

**Các mục 1–6 bên dưới là DRAFT tour contract từ bản tham khảo, chưa phải API đã triển khai hoặc contract freeze được xác nhận.**
H0 chưa chốt; `fixtures/tour.schema.json` chưa có. Không coi enum minh họa có dấu `|` là JSON Schema hợp lệ.
Hai view Creator/Viewer và audio tour đã được Thái yêu cầu ở `USER-VIEWS.md` và `TOUR-AUDIO.md`;
draft bên dưới chưa bao phủ draft/publish snapshot, nhạc nền và audio theo room/locale.
Backend gửi `CONTRACT_CHANGE` cho integrator để chốt schema + fixture trước khi viết API tour.

### API đang có thật: assistant intake

Source authority: `server/assistant/app.py`, `graph.py`; chi tiết chạy ở `docs/BACKEND-HANDOFF.md`.

| Endpoint | Input | Output / hành vi |
|---|---|---|
| `GET /api/assistant/state` | Cookie phiên nếu có | Tạo cookie khi thiếu, đọc state; không gọi model |
| `POST /api/assistant/turn` | JSON `text` (1–2000 ký tự), `request_id` (8–80 ký tự, chữ/số/gạch nối) | State sau LangGraph; cần cookie từ GET và Origin đúng cấu hình |
| `POST /api/assistant/voice` | `application/sdp`, SDP có audio | SDP từ upstream hoặc lỗi; key chỉ ở backend |

State gồm `profile`, `deferred`, `history`, `awaiting`, `stage`, `confirmed`, `reply`, `required`, `labels`, `configured`.
`configured` chỉ cho biết key/extractor có cấu hình, không xác minh key/model/quota.
`confirmed` là xác nhận hồ sơ intake, **không** là phê duyệt/publish tour.
Lỗi dùng `error` cho lỗi app trả chủ động; lỗi validation/HTTPException có `detail` theo FastAPI. Chưa có error envelope thống nhất.
Các API projects/demo/publish bên dưới **chưa có**; assistant chưa có property ID/tour ID hoặc dữ liệu spatial context.

## 1. Thư mục một project (output chung của core + ai, web chỉ đọc)

```text
projects/<id>/                  id = MMDD-HHMMSS-<method>
  project.json                  meta lúc tạo (ai ghi)
  input/                        file người dùng tải lên (ai ghi)
  work/                         trung gian, không commit (core/ai ghi)
  scene/                        file 3D cuối cho viewer (core ghi)
  frames/<frame_id>.jpg         khung đại diện + pose (core ghi)
  analysis.json                 kết quả AI xem ảnh (ai ghi)
  narration.mp3                 giọng đọc (ai ghi)
  status.json                   tiến độ từng bước (runner ghi)
  tour.json                     đầu vào duy nhất của tour viewer (bước publish ghi)
```

## 2. Pipeline — bước và chủ

| # | Bước | Lane | Vào | Ra |
|---|---|---|---|---|
| 1 | `ingest` | core | `input/` | `work/` chuẩn hoá |
| 2 | `reconstruct` | core | `work/` | `scene/<file>` + `scene.json` (`type`, `src`, `matrix`) |
| 3 | `keyframes` | core | scene | `frames/*.jpg` + `frames.json` (`id`, `pos`, `yaw`) |
| 4 | `analyze` | ai | `frames/` | `analysis.json` (rooms, furniture, materials, windows) |
| 5 | `domain` | ai | `analysis.json` + `project.json` | ví dụ bản tham khảo: nắng theo hướng cửa sổ |
| 6 | `script` | ai | các bước trên | `lines.json` (mỗi câu gắn `room`) |
| 7 | `voice` | ai | `lines.json` | `narration.mp3` + timings |
| 8 | `publish` | ai | tất cả | `tour.json` |

Runner (lane ai) gọi từng bước qua **một interface**: `run_step(project_dir, step) -> None`, raise khi lỗi.
Bước của core nằm trong `pipelines/core/`, runner chỉ import, không sửa.

## 3. `status.json`

```json
{
  "version": 1,
  "state": "queued | running | done | error",
  "steps": {
    "ingest": { "state": "pending | running | done | error | skipped", "seconds": 0.0, "log": ["[12:52:57] ..."] }
  },
  "error": null
}
```
Bước đã `done` thì bỏ qua khi chạy lại; `--from <step>` để chạy lại từ một bước.

## 4. HTTP API (lane ai, web gọi qua proxy `/api`)

| Method | Path | Body / Trả về |
|---|---|---|
| `POST` | `/api/projects` | multipart: `method`, `name`, `lat`, `lon`, `heading`, `files[]` → `{ "id": "..." }` |
| `POST` | `/api/demo/{method}` | chạy với input mẫu → `{ "id": "..." }` |
| `GET` | `/api/projects` | danh sách tóm tắt (không có `steps`) |
| `GET` | `/api/projects/{id}` | `{ ...project.json, "status": status.json, "inputs": [...], "hasTour": bool, "thumb": url }` |
| `GET` | `/projects/{id}/...` | file tĩnh trong thư mục project |

## 5. `tour.json` (v1 rút gọn)

```json
{
  "version": 1,
  "id": "1015-125257-d", "method": "D", "name": "...",
  "location": { "lat": 10.7769, "lon": 106.7009, "tz": 7, "label": "TP.HCM (giả định)" },
  "startHeading": 180,
  "house": { "title": "...", "summary": "...", "highlights": ["..."], "style": "..." },
  "scene": { "type": "splat | pano | mesh", "src": "scene/splat.spz", "matrix": [16 số] },
  "rooms": [{
    "id": "r1", "name": "...", "type": "...", "description": "...",
    "frames": ["v0_y0"], "best_frame": "v0_y0", "thumb": "frames/v0_y0.jpg",
    "view": { "pos": [0, 0, 0], "yaw": 0 },
    "furniture": [{ "name": "...", "note": "..." }],
    "materials": { "floor": "...", "walls": "...", "ceiling": "..." },
    "highlights": ["..."], "domain": {}
  }],
  "narration": { "audio": "narration.mp3", "total": 65.0,
                 "lines": [{ "id": "l1", "text": "...", "room": "r1 | null", "start": 0.0, "end": 3.2 }] },
  "credits": ["..."],
  "pipeline": [{ "step": "ingest", "label": "...", "seconds": 0.0 }]
}
```
`domain` là chỗ của logic riêng theo đề (bản tham khảo: `sun` gồm hướng cửa sổ + giờ nắng theo mùa).
Ví dụ đầy đủ: `../codex_hack/projects/1015-125257-d/tour.json`.

## 6. Fixture bắt buộc ở H0 (Dev 1 tạo)
- `fixtures/project-done/` — một project đủ file, `tour.json` hợp lệ, scene nhỏ (< 5 MB).
- `fixtures/status-running.json`, `fixtures/status-error.json` — cho UI tiến trình.
- `fixtures/tour.schema.json` — JSON Schema của `tour.json`; `scripts/gate.sh` kiểm mọi `tour.json` theo schema này.

## 7. Implemented vertical slice: `checkpoint-tour-v1` (product-sync)

Authority: explicit cross-lane PRODUCT INTEGRATION task, 2026-10-31. This is an additive,
separate manifest from the unimplemented reconstruction v1 above; no `/api/projects` alias is claimed.
Runtime schema: `server/tours/models.py`; checked-in JSON Schema + synthetic fixture:
`fixtures/tour.schema.json`, `fixtures/checkpoint-tour/tour.json`.
Existing `/api/assistant/*` request/response/cookie contracts remain unchanged. `/` now serves landing;
`experience.html` redirects to `/business/create` (Studio). Legacy `/creator.html` remains accessible. `/viewer.html`, assets and APIs share one origin.

Chat context extension: both tour chat endpoints accept optional `scene_id` (null or an existing
scene ID in that saved draft/published snapshot). Unknown IDs fail 422 before provider invocation.
Omission remains whole-tour context. Model input includes the validated current scene and at most
six successful conversation pairs, each message truncated to 1000 characters. Creator history is
private to its owned draft; Viewer history is isolated by session and immutable snapshot and never
reads the Creator's private conversation. Viewer remains read-only. Successful sequential replay of
the same request/body returns its stored answer; changed text/scene with the same ID returns 409.
Stored history is retained; the excerpt cap does not implement data deletion or exactly-once billing.
No manifest schema or existing-record migration is required. See `CHAT-FLOW-HANDOFF.md`.

- `schema_version=checkpoint-tour-v1`, `id`, `revision>=1`, `status=draft|published`, `title`,
  `locale=en|vi`, ordered `scenes[1..20]`, `start_scene_id`, `audio`, `credits`.
- Scene: server IDs `id`, `asset_id`; `name`, `description`; `projection=photo|cylindrical`,
  `coverage_degrees=null|30..360`, `coverage_source=unknown|user_provisional|user_calibrated`;
  server-owned `image_url` / `thumbnail_url`. Photo implies null/unknown coverage. Cylindrical
  requires explicit labelled coverage. No spherical/3D claim and no inferred coverage from dimensions.
- Legacy/keyless visual-only manifests use `status=unavailable`, `source=none`, `narration=null`, `music=null`.
  W2 recorded-audio extension is defined in §8; this old shape remains valid. Device voice is an opt-in
  fallback, never a recorded/OpenAI audio asset.
- UI content is user supplied, not automatically translated. Locale switches control labels; content
  language remains visible. No fabricated translations, image analysis, spatial pose or model output.

| Endpoint | Contract |
|---|---|
| `GET /api/tours/session` | Sets HttpOnly/SameSite Strict cookie scoped `/api/tours/` (30 days); lists only own drafts and configured AI flag |
| `POST /api/tours/assets` | Raw JPEG/PNG/WebP bytes, max 12 MiB; decode/verify/EXIF-orient, strip metadata, JPEG texture ≤8192 px and thumbnail ≤480×300; max 32M pixels, source side ≤16000; HEIC unsupported 415. Per-owner byte digest dedupe. ≤100 images/session. Returns asset ID/URLs/dimensions; projection unknown |
| `GET /api/tours/assets/{asset}` | Private image, owned session only; `?thumbnail=1` for thumbnail |
| `POST /api/tours/drafts` | `{asset_ids,title?,text?,locale,request_id}`; 1–20 distinct owned assets; IDs and neutral localized `Overview` / `Viewpoint N` labels generated server-side; omitted or legacy placeholder titles derive from the supplied description, with the first scene retaining that description; records same-turn text+asset references. Idempotent request ID, mismatch 409 |
| `GET /api/tours/drafts/{id}` | Own manifest; unknown/other owner 404 |
| `PUT /api/tours/drafts/{id}` | `{revision,title,locale,scenes,start_scene_id}`; scene fields exclude URL fields; exact existing scene→asset mapping required; name/order/calibration edit increments revision and invalidates review. Stale 409 |
| `POST /api/tours/drafts/{id}/review` | `{revision}` marks explicit reviewed revision; stale 409 |
| `POST /api/tours/drafts/{id}/publish` | `{revision}` requires matching saved+reviewed revision and readable images. Returns immutable snapshot with new ID and public asset URLs. Same draft+revision idempotent; later draft edits do not affect it |
| `GET /api/tours/published` | Published snapshots only; shareable within this local server; no private drafts |
| `GET /api/tours/published/{id}` | Immutable manifest, no cookie required |
| `GET /api/tours/published/{id}/assets/{asset}` | Only assets referenced by that snapshot, no cookie required |
| `POST /api/tours/drafts/{id}/chat` | `{text,request_id,revision,locale,scene_id?}`; text-only grounded assistant; can rename/describe/reorder/start only existing scene IDs. Revision checked after model response too. Returns `{reply,manifest,source}`; saved history, sequential request idempotency; no exactly-once promise for concurrent provider calls |
| `GET /api/tours/drafts/{id}/messages` | Own text+attachment IDs and successful chat responses, never image base64 |
| `POST /api/tours/published/{id}/chat` | Same chat body; only approved context, optional existing `scene_id` navigation; no draft write or publish tools |

All writes require exact `Origin=ASSISTANT_ORIGIN` and a tour session; JSON bodies capped at 64 KiB.
404 hides other owners' objects; 409 protects revisions; 415/413 report invalid/large images;
422 validates fields, 503 reports missing OpenAI key, 502/429 sanitize upstream failures.
FastAPI validation errors retain `detail`; UI accepts both legacy `error` and `detail`.
No login/account authorization is claimed. Cookie loss loses draft access; published URLs intentionally
remain accessible. Do not expose this unauthenticated local MVP to untrusted public traffic.

Persistence: SQLite + normalized image files under `TOUR_DATA_DIR` (default next to ASSISTANT_DB in
`projects/assistant/work/tours`). No production migration. Single local process/worker. Corrupt config
or inaccessible storage fails visibly; no shared existing DB/storage is opened.
OpenAI uses existing `OPENAI_API_KEY`/`OPENAI_MODEL_TEXT`, structured output, timeout 30s, retries=0,
1200 output tokens, `store=false`. Calls only on explicit chat submit. Integration QA uses no key or
injected test interpreters. No image analysis, TTS, GPU or paid live validation authorized/performed.


## 8. W2 recorded PCM WAV extension (feature/tour-audio)

Authority: `docs/work-items/W2-AUDIO.md`, explicit additive schema/API delegation. Existing
`checkpoint-tour-v1` manifests/routes remain valid. No dependency or provider changes.

### Media and provenance

- **Only RIFF PCM format 1 WAV, 16-bit little endian, mono/stereo.** Supported sample rates:
  8000, 11025, 16000, 22050, 24000, 32000, 44100, 48000 Hz. MP3/AAC/OGG/float WAV/HEIC audio
  or WAV extensible are not accepted. Error text explicitly states the supported encoding.
- Per-file ≤20 MiB and 0 < measured duration ≤180s; both limits apply (high-rate stereo may hit
  the byte cap sooner). ≤100 audio assets per cookie session. WAV byte signature, RIFF/chunk lengths,
  format/data uniqueness, frame alignment, byte rate and full PCM payload verified using stdlib
  `wave` plus RIFF bounds checks. Duration is frame count / sample rate, never client metadata.
- Stored normalized PCM WAV drops arbitrary metadata chunks. Random server IDs; no arbitrary URLs,
  paths, names or base64 accepted as playback references. Immutable files under `TOUR_DATA_DIR/audio/`;
  additive `audio_assets` table in the existing local tour SQLite DB. No change to existing records.
- Upload provenance required: `{source_label: string[3..200], rights: owned|licensed,
  rights_note: string[3..500]}`. These are the uploader's declarations, not independent license
  verification. Rendered safely as text. User must have permission to publish/share the recording.
- Identical normalized bytes + identical provenance deduplicate within an owner session; changing
  bytes or provenance creates a new ID. No old blob is overwritten or deleted by attach/remove.

### Endpoints

| Endpoint | Contract |
|---|---|
| `POST /api/tours/audio-assets` | Raw WAV body, session + exact Origin; `X-Audio-Metadata` is `encodeURIComponent(JSON.stringify(provenance))`, max 4096 header characters. Returns server `AudioTrack`; signature/encoding/truncation 415, limits 413, provenance 422 |
| `GET /api/tours/audio-assets/{id}` | Owner-only WAV, `audio/wav`; HTTP Range supported. Other session 404, missing session 401 |
| `PUT /api/tours/drafts/{id}/audio` | `{revision,music_asset_id:null|ID,narration:[{scene_id,asset_id,locale,transcript?}]}` fully replaces bindings, never files. Music optional; ≤20 narration bindings, unique scene/locale, existing scene and current source locale required. Track IDs must belong to draft owner. Increments revision and clears review, even on explicit reattachment; stale 409 |
| `GET /api/tours/published/{id}/audio/{asset_id}` | Cookie-free only if asset is referenced by that immutable snapshot. All other IDs 404; `audio/wav`, Range supported |

Existing publish requires exact reviewed revision and verifies every referenced audio asset still
exists and matches stored metadata. Snapshot rewrites private URLs to snapshot-owned public URLs.
Later draft edits/removal do not mutate those refs or bytes. Uploading alone does not attach/publish.

### Additive manifest audio shape

- `AudioTrack`: `asset_id`, server-owned `url`, `content_type=audio/wav`, measured `duration_seconds`,
  `channels=1|2`, `sample_rate`, `sample_width=2`, plus provenance fields above.
- `audio.music`: null or `AudioTrack`.
- `audio.narration`: null or ordered list of `{scene_id, locale:en|vi, transcript:string[0..2000], track:AudioTrack}`.
  Transcript is Creator supplied, not transcription or a guarantee of what the recording says.
- `audio.source`: `none` when empty; `user_uploaded` if any track exists. No AI/voice identity inference.
- `audio.status`: `unavailable` if no tracks; `ready` if every scene has a recording in the tour source
  locale (music is optional); `partial` otherwise. This describes attached media, not real-world quality
  or playback success. Viewer separately reports source/locale/load failure per current scene.
- Changing draft locale never relabels a recording. Old-language refs remain with `partial` status;
  Creator explicitly removes old narration before attaching replacements in the new source locale.
  Text/interface language switching never claims translated voice. Old null/unavailable shape still valid.

### Playback behavior

Click Play/resume is required. One HTMLMediaElement for narration and one for looping music, no
implicit generated voice. Independent mute/gain. While an audible narration is actually playing,
music gain = selected base gain ×0.2; restored on pause/end/wait/mute/error. Pause preserves both clocks.
Scene change cancels/reset old narration; if playback was active it plays the new scene from zero and
resumes the same music clock. Fast transitions invalidate prior play promises; no queued voices.
Seek controls current recording time. Recorded transcript (if supplied) follows the selected scene.

Opening/focusing chat, changing locale, pagehide or a hidden tab pauses/stops tour speech; closing
chat does not resume automatically. Missing narration/locale/load failures are explicit; visuals still
work and music may continue if available. Device voice is separate opt-in fallback only when no
recording is selected; starting it pauses both recorded tracks. It is never presented as uploaded/AI voice.

QA uses generated sine tones only, via actual upload/HTTP/media decode and clock/events. No test
recording is described as human narration or licensed background music. No paid API, keys, TTS,
asset download or production-data migration occurs in this task.

## P0 cached-home facade — 2026-10-31

Direct Thái scope: make the specifically supplied cached ZInD000 home visible in
Xem tour without changing Creator12-image limits or existing tour schemas.
Read-only `GET /api/demos` returns approved cached-demo cards (id/kind/title/href,
thumbnail_url, rooms/captures/markers, source_mode, rights_status, audio_available).
`GET /demos/zind-house-000` is the branded cached viewer; `GET|HEAD
/api/demos/zind-house-000/assets/{name}` serves only catalog members from private
MinIO, supports single Range206/416, returns404 for unknown IDs/paths and503 for
storage/hash metadata mismatch. No client filesystem path, rawZIP, BLEND, arbitrary
bucket key, dataset export or write API. Backend-only DEMO_CATALOG_PATH is optional;
if explicitly configured, invalid/missing catalog fails startup. Catalog/data and
renderer bundle remain outsideGit. Projection and room/capture/marker mapping
come from the pinned supplied manifest; existing Hackathon snapshot unchanged.

### Cached demo guide (direct Thái follow-up, 2026-10-31)
`GET /api/demos/{id}/intro` and `/guide` expose allowlisted generated-audio metadata/URLs. Guide preserves `capture_id`, `room_id`, `locale`, `script`, `description`, `source_id`, `source=openai_generated`, model/voice/script SHA/audio SHA/duration. It adapts the pinned TTS handoff; 15 rooms×2 locales =30 room bindings, expanded to16 selected markers×2 =32 capture bindings,16 unique WAVs. Sequence follows existing selected marker order, not physical adjacency. Missing locale stops, manual interaction/Pause/chat cancel auto-next, final capture finishes, no autoplay. Schema of existing immutable published tours unchanged.

## Demo UX — canonical Creator and immersive Viewer, 2026-10-31

User-authorized demo fixes preserve the manifest/API/storage schemas and source
locale default. `/business/create` now serves the photo Creator Studio using
`/api/tours/*`; `/creator.html` and `/experience.html` converge on that entry while
preserving draft/new query parameters. Existing `/business/projects/{id}/generate`
projects keep the original Studio runtime and `/api/studio/*` contracts. New
creation uses one limit: 20 images, 12 MiB each, as before for `/api/tours/assets`.

Creator explicitly selects content language, and Save retains it independently
of interface EN/VI. Creation without a configured assistant stores defaults from
the user's text and does not attempt chat. These defaults are deterministic copy,
not image analysis or an AI completion; room identity and spatial facts are not
inferred. Recorded audio fields live under Advanced; unavailable generated-voice
controls are hidden without weakening the backend's consent/budget checks.

Viewer presents both ordinary photos and cylindrical panoramas in one viewport.
Camera bounds account for visible rays and captured vertical/horizontal extent.
The chosen opening scene is presented first without mutating published ordering.
Unavailable AI/empty audio controls are hidden; a real narration track exposes a
Listen button. Source details are expandable. Interface switching does not
translate supplied text. An explicitly selected audio language is retained;
otherwise narration follows the interface locale, and locale changes pause playback. Chat
history/suggestions are page-local UI; existing server history boundaries remain.
Missing/provider AI errors preserve 503/429/502 while returning safe localized text.

## Studio library and late music (2026-10-31)

User-authorized additive integration: `GET /api/studio-tours` returns published
snapshot cards only (`id`, `title`, `thumbnail_url`, `viewer_url`, `format`,
`published_at`). Drafts, owner cookies and original descriptions remain private.
The main library combines these with legacy `/api/tours/published`.

`POST /api/studio/projects/{id}/music/placeholder` accepts an Action request ID
and attaches the bundled credited WAV. Existing `POST .../assets?kind=music`
replaces the draft music even after generation; spatial inputs remain frozen.
Publication resolves current music into an immutable snapshot without repeating
model/TTS work. Published projects reject music replacement/deletion with 409.
Published v1 schema stays unchanged.

Private Studio SSE also accepts `event_type=model_progress` with a cumulative
`progress` object: model, effort, phase, started_at (Unix milliseconds), elapsed_seconds,
reasoning_summary (public API summary only), plan_preview and output_characters.
It is replayable for the owner and never added to published v1 tour packages.
Raw reasoning events and encrypted model content are not forwarded.

Final Studio Review accepts optional `introduction` (1-1800 characters), alongside room scripts. The approved text is persisted before any TTS; published narration schema remains unchanged.

## Production entry integration — 2026-10-31

Explicit user choice supersedes the preceding photo-default routing:
`/business/create` serves AI/Blender Studio. `/business/photos` serves the existing
photo editor, and `/creator.html` preserves photo draft queries while normalizing
to `/business/photos`. `/experience.html` opens the default AI entry. The shared
library combines cached demos, Studio snapshots and legacy photo snapshots.
No published schema or existing snapshot is converted. Placeholder music is
covered by upload admission limits. The existing 20 MiB self-contained GLB limit
also applies to local Blender output.

## Seoul sample media exception — 2026-10-31

Explicit user authorization adds `GET /api/demos/seoul-apartment/exports` for
one reviewed, immutable English package. It returns locale, measured duration,
eight source capture chapters, and video/audio/transcript/captions objects with
same-origin `url` and `download_url`. Missing packages and every other demo ID
return 404. Only the pinned Seoul catalog can admit MP4/TXT/VTT export assets;
the four exact export filenames are validated with hashes, MIME and chapter bounds.
Asset GET/HEAD supports byte ranges and `?download=1` attachment headers for
these files. No generation endpoint, published schema or ZInD exception is added.
The landing preview and sample CTA now reference the same furnished Seoul model.
