---
slug: codex-hackathon
name: Codex Hackathon
type: project
status: active
priority:
deadline: sprint 12 tiếng (ngày chưa chốt)
one_liner: Sprint 12h, 3 dev, mỗi dev 1 Claude lead + ≤3 Codex worker song song; tham khảo House VR Tour (codex_hack).
updated: 2026-10-31
---

# Codex Hackathon — luật cho MỌI agent (Claude, Codex)

> Agent nào mở repo này cũng đọc theo thứ tự: **file này → `docs/CONTRACTS.md` → task card của mình**.
> Không đọc task card/lane khác trừ khi card yêu cầu. Lead đọc thêm `docs/ORCHESTRATION.md`.

## 1. Mục tiêu
Trong 12 tiếng, 3 dev ship một sản phẩm **demo được end-to-end** trên `main`, có link deploy và demo 3 phút.
Đề mặc định và cut-list: `docs/PRODUCT.md`. Sản phẩm tham khảo: `../codex_hack` (**chỉ đọc**).

## 2. Lane và ownership — một file, một chủ

| Lane | Dev | Ghi được | Ví dụ việc (theo bản tham khảo) |
|---|---|---|---|
| `web` | Dev 1 · **integrator** | `web/`, file root, `docs/CONTRACTS.md`, `fixtures/` | upload, tiến trình job, viewer, tour, deploy |
| `core` | Dev 2 | `pipelines/core/`, `tests/core/` | ingest, dựng 3D/xử lý nặng, keyframes, cache demo |
| `ai` | Dev 3 | `server/`, `pipelines/ai/`, `tests/ai/` | API job, VLM phân tích, logic miền, LLM viết lời, TTS |

File root (`package.json`, lockfile, `.gitignore`, `scripts/`, `AGENTS.md`) chỉ Dev 1 sửa. Lane khác cần đổi → ghi `NEED:` trong báo cáo.

## 3. Luật cứng cho agent làm task
1. **Chỉ ghi trong `Paths` của task card.** Cần đụng file khác → dừng phần đó, ghi `NEED: <file> — <lý do>`.
2. **Contract đóng băng từ H1.** Không tự đổi schema/API/tên file output. Cần đổi → ghi `CONTRACT_CHANGE:` và dừng.
3. **Làm trên fixture, đừng chờ lane khác.** Thiếu dữ liệu thật → dùng `fixtures/`, không tự bịa format mới.
4. **Timebox 45 phút.** Chưa xanh sau 45 phút hoặc sau 2 hướng sửa → dừng, báo `BLOCKED:` kèm giả thuyết.
5. **Không thêm dependency** ngoài card. Cần thì ghi `NEED: dep <tên>` (Dev 1 duyệt, vì lockfile chung).
6. **Không secret trong code/log/report.** Chỉ `.env.example`. Không gửi data ra dịch vụ ngoài khác với card.
7. **Job nặng (GPU/Kaggle/train > 10 phút) chỉ lane `core`/`ai` chạy**, chạy nền, tôn trọng lock, ghi log ra file.
8. **Không sửa `../codex_hack`.** Copy code từ đó chỉ khi mục ⚠️ cuối file đã được chốt là được phép.
9. **Không push `main`, không force-push, không merge.** Agent chỉ commit trên nhánh của mình; lead merge.
10. **Done = gate xanh + bằng chứng chạy thật**, không phải "code trông đúng".

## 4. Gate
`scripts/gate.sh <web|core|ai|all>` — build/lint/test/kiểm contract của lane. Từ H1 dùng `--strict` (SKIP = fail).
UI thì thêm bằng chứng nhìn thấy: screenshot hoặc log Playwright. Pipeline thì thêm output thật khớp contract.

## 5. Git
- Trunk-based. Nhánh `<lane>/<task-id>-<slug>`, worktree ở `../CodexHackathon-wt/<task-id>` (tạo bằng `scripts/spawn.sh`).
- Commit nhỏ, message `<lane>: <việc>`. PR/merge ≤ 90 phút một lần mỗi lane; `main` luôn xanh.
- `main` đỏ → **dừng mọi merge** cho tới khi Dev 1 xanh lại (andon).

## 6. Báo cáo cuối task (dòng cuối cùng của agent)
```text
STATUS: DONE | PARTIAL | BLOCKED
CHANGED: <file đã sửa>
EVIDENCE: <lệnh gate + kết quả rút gọn; screenshot/log path>
NEED: <file/dep/quyết định cần người khác, hoặc none>
CONTRACT_CHANGE: <đề xuất, hoặc none>
NOTES: <bẫy gặp phải, ≤3 dòng>
```

## Đang ở đâu
2026-10-31: mới có bộ luật + script điều phối; chưa có code sản phẩm, chưa có đề thật.

## Next action
- [ ] Thái chốt 3 mục ⚠️ dưới đây trước H0
- [ ] Pre-flight từng máy: `scripts/doctor.sh` (auth Codex/Claude, git, node, uv)
- [ ] H0: Dev 1 chạy kickoff theo `docs/ORCHESTRATION.md §3`

## Đang kẹt
Chưa có đề chính thức của hackathon và chưa có tên 3 dev.

## Quyết định đã chốt
| Ngày | Chốt gì | Vì sao |
|---|---|---|
| 2026-10-31 | 3 lane theo ranh giới của codex_hack (web / core / ai+server), contract-first | Ranh giới đã chứng minh chạy được; mỗi lane làm trên fixture nên song song từ H1 |
| 2026-10-31 | Codex = builder chạy song song trong worktree; Claude = lead lane, review chéo, tích hợp | Đề hackathon xoay quanh Codex; luôn có một con mắt khác nhà review |

## ⚠️ Cần Thái xác nhận
- [ ] Luật hackathon có cho mang code viết sẵn không? Không → chỉ mang `docs/`, `scripts/`, còn code từ codex_hack chỉ được đọc.
- [ ] Đề thật có phải House VR Tour v2 không? Khác → chỉ cần viết lại `docs/PRODUCT.md` + `docs/CONTRACTS.md` ở H0.
- [ ] Ai là Dev 1/2/3, mỗi người có máy GPU/Kaggle không (lane `core` cần nhất)?
