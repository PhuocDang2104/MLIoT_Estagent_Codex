# <task-id>: <việc, ≤ 8 từ>          <!-- task-id = <lane>-<NN>, vd web-03; tên file = <task-id>.md -->

<!-- Lead chép file này thành tasks/<lane>/<task-id>.md rồi chạy scripts/spawn.sh trên nó.
     Card tốt: 20–45 phút agent, một deliverable, Acceptance chạy được bằng lệnh. -->

Lane: <web|core|ai>
Slug: <ngắn-gạch-nối>          <!-- nhánh sẽ là <lane>/<task-id>-<slug> -->
Depends: <task-id đã merge, hoặc none>
Network: no                    <!-- yes chỉ khi card cần mạng (Kaggle, tải model); ghi rõ host trong Context -->

## Goal
<Kết quả đo được, một đoạn. Ví dụ: "trang job.html hiện 8 bước từ /api/projects/{id}, tự refresh 2s, dừng khi done/error".>

## Paths (chỉ được ghi ở đây)
- `web/job.html`
- `web/src/job.js`

## Context
- Contract liên quan: `docs/CONTRACTS.md §3` (status.json)
- Fixture: `fixtures/status-running.json`, `fixtures/status-error.json`
- Tham khảo (chỉ đọc): `../codex_hack/web/src/job.js`
- Bẫy đã biết: <copy dòng liên quan từ ../codex_hack/docs/RESULTS.md, hoặc none>

## Acceptance (agent tự chạy, dán kết quả vào EVIDENCE)
- `scripts/gate.sh web --strict` xanh
- <lệnh kiểm hành vi thật: curl / pytest / playwright screenshot ...>

## Out of scope
- <thứ dễ bị làm lan, ví dụ: không đổi style chung, không sửa server>
