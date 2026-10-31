# CONTRACTS — giao diện giữa 3 lane

## Additive: AI Generation Studio

Đọc `CREATOR-STUDIO.md` cho luồng LangGraph dài tại `/business/create`.
Luồng này dùng `/api/studio/*`, `/api/studio-tours/*` và cookie/storage riêng;
giữ nguyên `/api/tours/*`, schema Manifest và các trang Creator/Viewer hiện có.
Schema mới: `fixtures/studio-tour.schema.json`, fixture tổng hợp
`fixtures/studio-example/studio-tour.json`; gate kiểm cả hai bộ schema.
Studio có checkpoint persistence, SSE replay, spatial/final interrupt, worker
adapter, narration/TTS và immutable publish. Không có worker thì chờ integration
và chặn publish. Không giả dựng 3D hoặc tự suy panorama chỉ từ tỷ lệ ảnh.
Các endpoint, payload, giới hạn và điểm nối worker ghi trong card trên.

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
`experience.html` redirects to Creator. `/creator.html`, `/viewer.html`, assets and APIs share one origin.

- `schema_version=checkpoint-tour-v1`, `id`, `revision>=1`, `status=draft|published`, `title`,
  `locale=en|vi`, ordered `scenes[1..20]`, `start_scene_id`, `audio`, `credits`.
- Scene: server IDs `id`, `asset_id`; `name`, `description`; `projection=photo|cylindrical`,
  `coverage_degrees=null|30..360`, `coverage_source=unknown|user_provisional|user_calibrated`;
  server-owned `image_url` / `thumbnail_url`. Photo implies null/unknown coverage. Cylindrical
  requires explicit labelled coverage. No spherical/3D claim and no inferred coverage from dimensions.
- Audio truthfully reports `status=unavailable`, `source=none`, `narration=null`, `music=null`.
  Browser device voice is an opt-in fallback for original-language descriptions, not an audio asset.
- UI content is user supplied, not automatically translated. Locale switches control labels; content
  language remains visible. No fabricated translations, image analysis, spatial pose or model output.

| Endpoint | Contract |
|---|---|
| `GET /api/tours/session` | Sets HttpOnly/SameSite Strict cookie scoped `/api/tours/` (30 days); lists only own drafts and configured AI flag |
| `POST /api/tours/assets` | Raw JPEG/PNG/WebP bytes, max 12 MiB; decode/verify/EXIF-orient, strip metadata, JPEG texture ≤8192 px and thumbnail ≤480×300; max 32M pixels, source side ≤16000; HEIC unsupported 415. Per-owner byte digest dedupe. ≤100 images/session. Returns asset ID/URLs/dimensions; projection unknown |
| `GET /api/tours/assets/{asset}` | Private image, owned session only; `?thumbnail=1` for thumbnail |
| `POST /api/tours/drafts` | `{asset_ids,title?,text?,locale,request_id}`; 1–20 distinct owned assets; IDs and default `Photo N` labels generated server-side; records same-turn text+asset references. Idempotent request ID, mismatch 409 |
| `GET /api/tours/drafts/{id}` | Own manifest; unknown/other owner 404 |
| `PUT /api/tours/drafts/{id}` | `{revision,title,locale,scenes,start_scene_id}`; scene fields exclude URL fields; exact existing scene→asset mapping required; name/order/calibration edit increments revision and invalidates review. Stale 409 |
| `POST /api/tours/drafts/{id}/review` | `{revision}` marks explicit reviewed revision; stale 409 |
| `POST /api/tours/drafts/{id}/publish` | `{revision}` requires matching saved+reviewed revision and readable images. Returns immutable snapshot with new ID and public asset URLs. Same draft+revision idempotent; later draft edits do not affect it |
| `GET /api/tours/published` | Published snapshots only; shareable within this local server; no private drafts |
| `GET /api/tours/published/{id}` | Immutable manifest, no cookie required |
| `GET /api/tours/published/{id}/assets/{asset}` | Only assets referenced by that snapshot, no cookie required |
| `POST /api/tours/drafts/{id}/chat` | `{text,request_id,revision,locale}`; text-only grounded assistant; can rename/describe/reorder/start only existing scene IDs. Revision checked after model response too. Returns `{reply,manifest,source}`; saved history, sequential request idempotency; no exactly-once promise for concurrent provider calls |
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
