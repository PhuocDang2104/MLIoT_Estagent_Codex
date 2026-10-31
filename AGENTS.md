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
> Codex worker đọc thêm `docs/CODEX-OPENAI.md`; task dùng OpenAI API phải điền mục **OpenAI** trong card.
> Teammate backend bắt đầu từ `docs/BACKEND-HANDOFF.md` và `server/AGENTS.md`. Không cần Tatejo/herdr hoặc đường dẫn riêng của máy Thái để chạy repo.
> Phân vai thêm theo yêu cầu của Thái: Claude review chỉ đọc, Cursor/Grok build nhỏ/review và agy review nội dung; phạm vi/trạng thái tại `docs/PROVIDER-LANES.md`. Không cấp quyền commit/metadata cho reviewer.

## 1. Mục tiêu
Trong 12 tiếng, 3 dev ship một sản phẩm **demo được end-to-end** trên `main`, có link deploy và demo 3 phút.
Đề mặc định và cut-list: `docs/PRODUCT.md`. Sản phẩm tham khảo: `../codex_hack` (**chỉ đọc**).
Máy không có `../codex_hack` thì giải nén `codex_hack-ref.tgz` (Thái tạo bằng `scripts/pack-ref.sh`, gửi riêng, **không commit**) cạnh repo.

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
11. **Bắt buộc declare nguồn và phần build trong thời gian thi** theo `docs/DECLARATION.md`. Copy/adapt source cũ, dependency, model/API, asset và data/cache đều phải ghi; commit hôm nay không chứng minh code viết hôm nay. Worker khai trong `NOTES`; Dev 1 tổng hợp trước khi nộp.

## 4. Gate
`scripts/gate.sh <web|core|ai|all>` — build/lint/test/kiểm contract của lane. Từ H1 dùng `--strict` (SKIP = fail).
UI thì thêm bằng chứng nhìn thấy: screenshot hoặc log Playwright. Pipeline thì thêm output thật khớp contract.

## 5. Git
- Quyết định trực tiếp của Thái (2026-10-31): root Tatejo chỉ điều phối, review và nghiệm thu; không trực tiếp implementation hoặc SSH rollout. Lane integration/release được giao thực thi merge/resolve/push main và deploy trong scope đã ủy quyền; lane UI implement Viewer. Không force-push main. Quy trình và handback tại `docs/CODE-INTEGRATION.md`.
- Trunk-based. Nhánh `<lane>/<task-id>-<slug>`, worktree ở `../CodexHackathon-wt/<task-id>` (tạo bằng `scripts/spawn.sh`).
- Commit nhỏ, message `<lane>: <việc>`. PR/merge ≤ 90 phút một lần mỗi lane; `main` luôn xanh.
- `main` đỏ → **dừng mọi merge** cho tới khi Dev 1 xanh lại (andon).
- Không thêm trailer `Co-Authored-By` cho Claude/Anthropic; giữ tác giả người thật và khai báo AI hỗ trợ trong `docs/DECLARATION.md`. Không dùng `--no-verify` để bỏ kiểm tra.
- Mỗi clone bật hook bằng `git config --local core.hooksPath .githooks` (nếu đã có hook riêng thì tích hợp checker, không ghi đè cấu hình đó). Trước push chạy `python3 scripts/check_commit_attribution.py --all`.

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
2026-10-31: Demo UX đã deploy source fc3fdd3 (giữ concurrent main279da1a và guide-v2/TTS/export). Strict web/AI, localhost create→publish và production GET-only desktop/mobile PASS; core strict vẫn SKIP. Creator canonical `/business/create`, ảnh thường và panorama chung Viewer toàn màn hình. Production keyless1/narration0/video1/MinIO; original manifest+8images không đổi. Metadata/rollback: `deploy/evidence/demo-ux-release/release.json`, `docs/DEMO-UX-HANDOFF.md`. Main có thể thêm commit evidence-only sau deployed SHA.
2026-10-31 — quyết định vai trò mới nhất của Thái: root Tatejo chỉ điều phối, review và nghiệm thu, không trực tiếp implementation/SSH rollout. Lane integration/release là owner thực thi maintain `main`, merge/resolve/push và SSH/deploy production theo scope Thái đã giao; lane UI implement Viewer. Quyền đã giao tiếp tục hiệu lực, không thêm vòng approval; tin nhắn điều phối không phải phê duyệt mới của Thái. Đích hiện tại là VM + DuckDNS `estagent.duckdns.org`; Vercel đã gỡ theo chỉ đạo mới. Không đổi stack/DB của project khác. Runbook và trạng thái thật: `docs/DEPLOYMENT.md`.
Checkout `main` đã tích hợp same-origin landing/Creator/Viewer, upload ảnh/chat, draft/review/publish snapshot, FastAPI/LangGraph/SQLite, audio WAV người dùng tải lên và Studio từ teammate. Chạy `bash scripts/dev.sh`; đọc `docs/INTEGRATION-HANDOFF.md`, `docs/AUDIO-HANDOFF.md`, `docs/CREATOR-STUDIO.md`. Cached Nhà Demo + actual OpenAI guide EN/VI đã lên production; generation mới vẫn tắt. Video FFmpeg/MinIO đã kiểm thật trên image tích hợp. Core reconstruction chưa nghiệm thu; fixture tones không phải giọng thật. Thông tin bootstrap bên dưới là lịch sử chuẩn bị.
2026-10-31: có bộ luật + script điều phối (`spawn/review/done/gate/doctor/pack-ref`, đã chạy thử với codex giả); chưa có code sản phẩm.
Remote chính: `github.com/PhuocDang2104/MLIoT_Estagent_Codex` (nhánh `main`). Remote cũ giữ dưới tên `previous-origin` để đối chiếu; không push các nhánh backup chứa attribution cũ.
Đã thêm quy định khai báo nguồn/build trong ngày thi ở `docs/DECLARATION.md`; mốc H0 và phân loại thực tế còn chờ xác minh.

## Next action
- [ ] Thái chốt 3 mục ⚠️ dưới đây trước H0
- [ ] Pre-flight từng máy: `scripts/doctor.sh` (auth Codex/Claude, git, node, uv)
- [ ] H0: Dev 1 chạy kickoff theo `docs/ORCHESTRATION.md §3`

## Đang kẹt
Production đã tích hợp pitch UX, cached Nhà Demo và guide thật EN/VI/auto-next, native Video/MinIO. Source/image/evidence mới nhất: `status/web.md` và `deploy/evidence/landing-model/release.json`. Strict còn core SKIP; global chat/realtime và TTS generation mới vẫn tắt. Manifest/rollback: `docs/DEPLOYMENT.md`; local integration: `docs/INTEGRATION-HANDOFF.md`.
Chưa có đề chính thức của hackathon và chưa có tên 3 dev.

## Quyết định đã chốt
| Ngày | Chốt gì | Vì sao |
|---|---|---|
| 2026-10-31 | MVP không cần auth; hoãn đăng nhập/đăng ký/email xác thực và Resend. Supabase chỉ dùng database/storage qua backend | Thái xác nhận trực tiếp; ưu tiên chat/voice và luồng tour |
| 2026-10-31 | 3 lane theo ranh giới của codex_hack (web / core / ai+server), contract-first | Ranh giới đã chứng minh chạy được; mỗi lane làm trên fixture nên song song từ H1 |
| 2026-10-31 | Codex = builder chạy song song trong worktree; Claude = lead lane, review chéo, tích hợp | Đề hackathon xoay quanh Codex; luôn có một con mắt khác nhà review |

## ⚠️ Cần Thái xác nhận
- [ ] Luật hackathon có cho mang code viết sẵn không? Không → chỉ mang `docs/`, `scripts/`, còn code từ codex_hack chỉ được đọc.
- [ ] Đề thật có phải House VR Tour v2 không? Khác → chỉ cần viết lại `docs/PRODUCT.md` + `docs/CONTRACTS.md` ở H0.
- [ ] Ai là Dev 1/2/3, mỗi người có máy GPU/Kaggle không (lane `core` cần nhất)?
- [ ] Repo đang PUBLIC: luật hackathon có bắt buộc public không? Không → chuyển private cho tới lúc nộp.
