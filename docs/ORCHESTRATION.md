# ORCHESTRATION — điều phối 3 dev × agent trong 12 tiếng

> Dành cho người và Claude lead. Agent worker chỉ cần `AGENTS.md` + task card.

## 1. Đội hình

```text
               Dev 1 (integrator, lane web)      Dev 2 (lane core)          Dev 3 (lane ai)
                 │                                 │                          │
       Claude lead #1 (main checkout)    Claude lead #2              Claude lead #3
        ├─ Codex worker web-01..03        ├─ Codex core-01..03        ├─ Codex ai-01..03
        └─ gate all + merge main          └─ job nặng chạy nền        └─ job Kaggle/LLM chạy nền
```

| Vai | Ai | Làm gì | Không làm |
|---|---|---|---|
| **Dev (người)** | 3 người | Chốt sản phẩm trong lane, duyệt merge, xử lý `BLOCKED`, test tay UI | Ngồi đọc từng token của agent |
| **Claude lead** | 1 phiên Claude Code/dev, ở checkout chính | Chia lane thành task card, chạy `scripts/spawn.sh`, review diff, chạy gate, merge nhánh lane, debug khó | Tự viết code lớn khi worker đang rảnh |
| **Codex worker** | ≤ 3 cùng lúc/dev, mỗi cái một worktree | Làm đúng 1 task card 20–45 phút, commit trên nhánh, trả báo cáo theo `AGENTS.md §6` | Sửa ngoài `Paths`, đổi contract, merge |
| **Review chéo** | Khác nhà với người viết | Diff do Codex viết → Claude lead review; diff do Claude viết → `scripts/review.sh` (Codex review) | Tự review code của chính mình |

Trần: **≤ 4 agent đang chạy/dev** (1 lead + 3 worker), ~12 toàn đội. Nhiều hơn thì lead không review kịp, merge thành nút cổ chai.

## 2. Vòng đời một task

```text
lead viết card (tasks/<lane>/<id>.md)  →  scripts/spawn.sh tasks/<lane>/<id>.md   (chạy nền)
  → worktree + nhánh riêng → gate smoke trong worktree → codex exec
  → báo cáo ở tasks/<lane>/<id>.report.md → runtime đánh thức lead
lead: đọc báo cáo → xem diff → gate lane → review chéo → merge nhánh vào main → xoá worktree
```

- **Card** dùng `docs/briefs/TASK-TEMPLATE.md`. Một card = một deliverable, có `Paths` + `Acceptance` chạy được bằng lệnh.
- **Không poll.** Lead chạy `spawn.sh` ở chế độ nền và làm việc khác (viết card kế tiếp, review). Runtime sẽ báo khi xong.
- **Fail 2 lần cùng card** → không spawn lần 3: dev tự làm, cắt nhỏ card, hoặc đưa vào cut-list.
- Báo cáo có `NEED:`/`CONTRACT_CHANGE:` → chuyển ngay cho chủ file (Dev 1 nếu là file root/contract).

## 3. Lịch 12 tiếng

| Giờ | Dev 1 · web + integrator | Dev 2 · core | Dev 3 · ai | Cổng ra |
|---|---|---|---|---|
| **H-1** (trước giờ G, nếu luật cho) | `scripts/doctor.sh` cả 3 máy · tạo repo private · đọc tham khảo | đo môi trường GPU/Kaggle, tải sẵn model | auth API/LLM, quota | 3 máy `doctor` xanh |
| **H0:00–0:45** kickoff | Chốt đề → `PRODUCT.md`; chốt `CONTRACTS.md` v1; tạo skeleton + `fixtures/` + gate | Lead đọc `../codex_hack` phần core, viết 6–9 card | Như Dev 2, phần ai/server | **Contract freeze v1** · skeleton xanh trên `main` |
| **H0:45–4:00** wave 1 | UI chạy trên fixture: tạo job, tiến trình, viewer | **Trước H1:30 khởi chạy job nặng tạo data demo** (chạy nền) · pipeline bước 1–3 | API job + `status.json` thật · VLM/LLM trên ảnh mẫu | mỗi lane ≥ 2 merge |
| **H4:00** sync #1 (15') | Demo vertical slice e2e (được phép mock 1–2 bước) | Báo ETA job nặng | Báo chất lượng AI trên data mẫu | Cắt scope theo cut-list |
| **H4–8** wave 2 | Thay fixture bằng output thật, polish tour | Output thật khớp contract, cache vào `demo-cache/` | Nối pipeline đầy đủ, TTS, đồng bộ lời ↔ camera | **Golden path chạy trên data thật** |
| **H8:00** sync #2 (15') | Chạy demo script trên `main` | | | Chốt danh sách tính năng cuối |
| **H8–10** wave 3 | Deploy bản tĩnh, mobile, lỗi UX | Fallback: tour dựng sẵn khi job live lỗi | Fallback: lời/giọng cache sẵn | Deploy link sống |
| **H10:00** | **FEATURE FREEZE** — chỉ bugfix, mỗi fix phải có Dev 1 duyệt | | | |
| **H10–11:30** | README, slide, quay video demo | Đo số liệu thật cho slide (thời gian, kích thước) | Kiểm lời/giọng, ghi giấy phép model | Demo chạy 2 lần từ clone sạch |
| **H11:30–12** | Buffer + nộp bài | | | Nộp |

**Mỗi giờ tròn:** mỗi lead ghi 3 dòng vào `status/<lane>.md` (xong · đang làm · kẹt). Một file một chủ nên không conflict.
Dev 1 đọc cả ba, chỉ gọi họp khi có `BLOCKED`, `MAIN_RED` hoặc cần cắt scope.

## 4. Luật tốc độ (rút từ codex_hack)

1. **Contract trước, code sau.** 45 phút đầu ngưng mọi code sản phẩm cho tới khi `CONTRACTS.md` + fixture có trên `main`.
2. **Việc dài khởi động sớm nhất.** Ở bản tham khảo, dựng 3D từ video mất ~35 phút, AI xem ảnh ~5 phút, giọng ~3 phút/project,
   Kaggle tối đa 2 phiên GPU. Mọi job > 10 phút phải chạy nền từ wave 1 và cache kết quả.
3. **Golden path + fallback.** Demo chạy trên data đã cache; đường live chỉ là phần thưởng. Không demo thứ chưa chạy ít nhất 2 lần.
4. **Mock có hạn dùng.** Mỗi mock ghi `MOCK:` trong code + `status/<lane>.md`; H8 mà còn mock trong golden path → báo sync #2.
5. **Merge nhỏ và đều** (≤ 90 phút/lane). Nhánh sống quá 2 giờ gần như chắc chắn conflict.
6. **Đổi contract sau H1** chỉ khi Dev 1 duyệt, theo kiểu chỉ thêm field (additive), bump `version`, sửa fixture trong cùng commit.
7. **Bẫy đã biết** — đọc `../codex_hack/docs/RESULTS.md` mục "Bẫy" trước khi viết card cho phần tương ứng.

## 5. Sự kiện cần người can thiệp

| Event | Ai xử | Xử thế nào |
|---|---|---|
| `BLOCKED` | Dev của lane | Đọc giả thuyết của agent; cắt card hoặc tự làm |
| `NEED` / `CONTRACT_CHANGE` | Chủ file (thường Dev 1) | Duyệt/từ chối trong 10 phút; đừng để worker chờ |
| `MAIN_RED` | Dev 1 | Dừng merge toàn đội, revert hoặc fix ngay |
| Job nặng fail | Dev 2/3 | Chuyển sang data cache/fallback, không chạy lại mù quá 1 lần |
| Lane trễ > 1h so với lịch | Cả đội ở sync gần nhất | Cắt theo `PRODUCT.md` cut-list, không thức đêm vá |

## 6. Lệnh

```bash
scripts/doctor.sh                                  # kiểm máy trước giờ G
scripts/spawn.sh tasks/web/web-03.md               # worktree + Codex worker (lead chạy nền)
CODEX_DRY=1 scripts/spawn.sh tasks/web/web-03.md   # chỉ dựng worktree + in prompt, không gọi Codex
scripts/review.sh web/web-03-upload-form           # Codex review nhánh so với main
scripts/gate.sh web --strict                       # gate một lane; `all` cho main
scripts/done.sh web/web-03-upload-form             # sau khi merge: xoá worktree + nhánh
```
