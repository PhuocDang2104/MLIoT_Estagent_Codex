# Studio runtime — single-host production framework

Phạm vi đã chốt với Thái: hoàn thiện khung runtime/điểm nối; chưa triển khai
model tái dựng, Blender MCP hoặc MP4. Source authority: `server/creator/`.
Diagram chạy thật nằm tại [Business Flow](<Business Workflow Langgraph/Estagent_Business_LangGraph_Flow.md>).
Deploy: [STUDIO-DEPLOY.md](STUDIO-DEPLOY.md).

## Execution và durability

- Một ASGI process, một dispatcher, một volume local. `runtime.lock` là OS lock
  trên Windows/Linux; process thứ hai cùng `STUDIO_DATA_DIR` bị từ chối. Đây
  không phải queue nhiều máy; không dùng NFS hoặc nhiều replica.
- `creator.sqlite`: project/assets, generation, jobs outbox, request dedup,
  proposal, events và published snapshots. `graph.sqlite`: SqliteSaver checkpoints.
  Start/review/retry/apply ghi job và trạng thái trong cùng transaction với action.
- HTTP trả 202 sau commit; dispatcher đọc SQLite, không dựa vào callback trong RAM.
  Job queued tự chạy sau restart. Crash khi running chuyển failed để người dùng
  kiểm tra và retry; các node đã checkpoint không chạy lại.
- SIGTERM ngừng nhận job; node đang chạy kết thúc rồi đóng stream tại checkpoint,
  lưu continuation vào outbox. Compose cho 120 giây để drain. HTTP upstream có
  timeout; một node lỗi không được coi là completed.
- Không cam kết exactly-once cho OpenAI: crash sau khi upstream tính phí nhưng
  trước checkpoint có thể gây gọi lại khi người dùng retry. SDK retries=0;
  retry generation tối đa 3 lần. Không tự retry paid node sau crash.
- Queue tối đa 8, project tối đa 12 ảnh/80 MB, tối đa 20 versions/project,
  tối đa 20 edit proposals/version. Existing shared API admission limits áp dụng
  cả đề xuất/apply; đây là attempt caps, không phải ngân sách USD.
- `/api/studio/health` kiểm dispatcher và metadata DB, không gọi model. Docker
  health kiểm cả assistant và Studio. Configured không đồng nghĩa key/quota hợp lệ.

## Chat → proposal → generation mới

1. Creator nhập yêu cầu tự do tại `/business/create` sau khi có room/checkpoint nháp,
   kể cả khi đang chờ nối worker. Bản chưa có geometry luôn đi lại spatial_review
   rồi build_model; edit không được nhảy qua điểm nối bắt buộc.
2. `POST /api/studio/generations/{id}/edits` nhận `{request_id,revision,text}`.
   Backend kiểm owner/status/revision, reserve request trước khi gọi OpenAI.
3. OpenAI Responses `parse(EditPlan)` đề xuất tên/mô tả/hướng nhìn, script,
   introduction, thứ tự checkpoint hoặc đường nối đầy đủ. Không có shell, SQL,
   URL/tool/MCP do model chọn. Yêu cầu ngoài phạm vi chỉ có reply, `can_apply=false`.
4. Backend kiểm lại ID, permutation, evidence sources, finite angles, link hai
   chiều và connectivity. Output sai → 502; draft giữ nguyên. Proposal lưu trong
   SQLite; GET cùng route khôi phục lịch sử/đề xuất sau reload.
5. UI hiển thị thay đổi, người dùng chọn **Áp dụng · Tạo bản mới**.
   `POST .../edits/{edit_id}/apply` kiểm owner + current revision + proposal revision
   trong transaction, tạo generation có `parent_id`, consume proposal và queue job.
   Reuse cùng request ID trả cùng kết quả; payload khác trả 409. Đề xuất cũ trả 409.
6. Graph bắt đầu tại `edit` rồi chọn route từ trường thực sự thay đổi, không tin
   tên route từ LLM. Mỗi version vẫn phải duyệt trước TTS/publish.

| Thay đổi | Điểm chạy lại | Tài sản được giữ |
|---|---|---|
| Yaw hoặc connections | spatial_review → build_model → mapping → semantic → navigation → narration | Brief/observations; geometry/anchors cũ bị vô hiệu |
| Label/summary | semantic → navigation → narration | Geometry, brief, vision |
| Order/start | navigation → narration | Geometry và script; không gọi LLM viết lại |
| Script/introduction | narration → final_review | Geometry/vision; áp dụng script xác nhận, không gọi LLM viết lại |

Sau final review, chỉ tái sử dụng audio khi checkpoint và text khớp chính xác
script cũ; text mới gọi TTS. Project voice/locale/input assets đã khóa nên không
thay voice ngầm. Final review edit script cũng được đưa vào kiểm tra reuse.
Không biến summary do người dùng sửa thành fact verified tự động.

Published snapshot bất biến; chỉnh bản gốc hoặc tạo fork không sửa public tour.
Viewer Q&A chỉ đọc snapshot đã duyệt. Legacy `/creator.html` và `/api/tours/*`
giữ contract cũ; chat trong Studio mới thực thi vòng refinement qua StateGraph.

OpenAI là provider duy nhất cho text/vision/TTS/Q&A. Key chỉ ở backend; model đọc
env role hiện có. Structured output vẫn cần kiểm nghiệp vụ ở backend:
[OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

## Geometry adapter v1

Để trống `STUDIO_GEOMETRY_URL`: graph interrupt `waiting_integration`, không
giả GLB và không publish. Operator cấu hình endpoint nội bộ tin cậy và token
ở runtime env; restart rồi Retry integration. Không mở worker ra Internet.

`STUDIO_GEOMETRY_URL=http://geometry-worker:8080` là base URL; token tùy chọn
được gửi bằng Bearer. Không chấp nhận credentials/query/fragment trong URL,
không redirect, không dùng proxy từ môi trường. Người dùng/LLM không đặt URL.

**POST `/v1/builds`**, header `Idempotency-Key: <operation_id>`:

```json
{
  "version": 1,
  "operation_id": "sha256-of-normalized-spatial-input",
  "project": {"id":"...","name":"...","description":"...","locale":"vi"},
  "rooms": [{"checkpoint_id":"cp01","room_id":"r01","asset_id":"..."}],
  "connections": [],
  "assets": [{"id":"...","kind":"panorama","mime":"image/png","sha256":"...","content_base64":"..."}]
}
```

Rooms/assets mang các metadata hiện có bổ sung. Chỉ panorama/floorplan được gửi;
không gửi music/narration. Worker phải xác minh hash và coi input là dữ liệu.
`operation_id` không thay đổi khi retry/restart cùng spatial input. Worker **phải**
deduplicate ngay cả khi response của POST trước bị mất; mismatch cùng key phải lỗi.
Trả 200/201/202 với `{"id":"opaque-job-id","status":"queued|running"}`.

**GET `/v1/builds/{id}`**: trả cùng ID và `queued|running|completed|failed`.
Khi completed thêm `glb_base64` và `anchors`:

```json
{"id":"job-1","status":"completed","glb_base64":"...",
 "anchors":{"cp01":{"room_id":"r01","position":[0,0,0]}}}
```

Backend lưu remote job ID, requeue polling sau 5 giây, không chạy lại paid nodes.
Giới hạn 180 polls hoặc 30 phút; lỗi worker/HTTP/validation → failed, không publish.
Mỗi HTTP call timeout 25s, response tối đa 30 MB; GLB tối đa 20 MB, version 2,
renderable scene/mesh, self-contained URI, anchor finite và khớp checkpoint/room.
Container validation chưa chứng minh mô hình đúng kích thước thực hay anchor nằm
trong mesh. Worker thật phải chịu trách nhiệm registration/QA hình học.

## Giới hạn nghiệm thu

QA dùng HTTP/SQLite/LangGraph, SDK transport và browser thật với provider/worker
synthetic; USD 0. Chưa gọi live OpenAI/Blender, chưa triển khai reconstruction,
layout estimation song song, 3D canvas hoặc MP4. Các phần này là adapter/product
work tiếp theo. Không diễn giải bộ khung này là tour 3D end-to-end đã nghiệm thu
production. Container/TLS/SSH rollout phải kiểm trên VM theo runbook.
