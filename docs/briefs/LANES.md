# LANES — backlog gợi ý theo bản tham khảo

> Lead dùng làm điểm xuất phát để viết card; được bỏ, gộp, đổi thứ tự theo đề thật.
> Cột "Tham khảo" là file trong `../codex_hack` (chỉ đọc). Thời gian là số đo thật trên M2 ở bản tham khảo.

## web — Dev 1 (integrator)

| Card | Việc | Tham khảo |
|---|---|---|
| web-00 | Skeleton Vite + gate + `fixtures/` + `tour.schema.json` (Dev 1/Claude tự làm ở H0, không giao worker) | `web/package.json`, `web/vite.config.js` |
| web-01 | Viewer scene theo `scene.type` (splat / pano / mesh), đọc từ `tour.json` | `web/src/splat.js`, `pano.js`, `mesh.js` |
| web-02 | Trang tạo tour: chọn cách, kéo thả file, vị trí + hướng, nút demo mẫu | `web/create.html`, `src/create.js` |
| web-03 | Trang tiến trình 8 bước từ `/api/projects/{id}` | `web/job.html`, `src/job.js` |
| web-04 | Tour: panel phòng + danh sách phòng + nhảy camera tới `view` | `web/src/tour.js` |
| web-05 | Phát narration, camera bay theo `lines[].room`, tua giữa bài vẫn đúng phòng | `web/src/tour.js` |
| web-06 | Trang chủ + tour mẫu; mobile 390px | `web/index.html`, `src/home.js` |
| web-07 | Build tĩnh + deploy (chép project cache vào `dist/projects`) | `web/tools/export-static.mjs` |

## core — Dev 2

| Card | Việc | Tham khảo |
|---|---|---|
| core-01 | **Khởi chạy ngay** job dựng data demo cho cách nặng (B ~26 phút, C ~17 phút) và cache | `pipelines/video2splat.sh`, `vggt_kaggle.py` |
| core-02 | `ingest` theo từng cách (ffmpeg tách frame, kiểm định dạng) | `pipelines/run_project.py` |
| core-03 | `reconstruct` A: cubemap → equirect, xếp pano (vài giây) | `pipelines/cube2equirect.py` |
| core-04 | `reconstruct` D: import `.ply/.spz/.glb`, dò sàn; giữ nguyên `.spz/.sog` | `run_project.py`, bẫy LoD |
| core-05 | `keyframes`: cắt 4 hướng từ pano (A) / render từ splat (D) + `frames.json` | `web/tools/render_views.mjs` |
| core-06 | `reconstruct` B: COLMAP + Brush, căn hệ toạ độ | `video2splat.sh`, `colmap_frame.py` |
| core-07 | Test output của core khớp `CONTRACTS.md §2` trên fixture | — |

Bẫy phải chép vào card: SPZ phải v3 (`--spz-version 3`); không chuyển mã `*-lod.spz`; parser COLMAP không bỏ dòng trống;
rig headless cần warm-up ~240 frame; Vite dev full-reload trang rig khi sửa source.

## ai — Dev 3

| Card | Việc | Tham khảo |
|---|---|---|
| ai-01 | Server FastAPI: tạo project, upload, demo, list/get, phục vụ file tĩnh (cổng tránh 8765) | `server/app.py` |
| ai-02 | Runner 8 bước, `status.json`, `--from`, interface `run_step` | `pipelines/run_project.py` |
| ai-03 | `analyze`: VLM trên `frames/` → `analysis.json` (khoảng 5 phút trên Kaggle T4) | `pipelines/vlm_kaggle.py`, `kaggle_job.py` |
| ai-04 | `domain`: logic miền (bản tham khảo: NOAA nắng theo hướng cửa sổ) | `pipelines/sun.py` |
| ai-05 | `script`: LLM viết lời, mỗi câu gắn phòng, cấm nêu diện tích khi không có tỉ lệ mét | `pipelines/llm.py` |
| ai-06 | `voice`: TTS + timings (khoảng 3 phút/project) | `pipelines/voice.py` |
| ai-07 | `publish`: ghép `tour.json` đúng schema | `run_project.py` (hàm publish) |

Bẫy phải chép vào card: Kaggle tối đa 2 phiên GPU, script kernel > ~1 MB bị từ chối (payload base64 ×1,33);
Kaggle Python 3.13 không có wheel `pycolmap==3.10`; script con chạy từ env uv phải dùng đúng interpreter (đưa lên đầu PATH).
