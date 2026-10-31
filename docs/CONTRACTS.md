# CONTRACTS — giao diện giữa 3 lane

> **Trạng thái: v0 nháp** (rút từ `../codex_hack`). Dev 1 sửa theo đề thật rồi **freeze v1 trước H0:45**.
> Chủ file: Dev 1. Sau freeze chỉ được thêm field (additive), bump `version`, sửa `fixtures/` trong cùng commit.
> Lane nào cũng code dựa trên fixture trong `fixtures/`, không chờ lane khác.

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
