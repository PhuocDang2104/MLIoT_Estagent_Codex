# Phân vai provider — Thái yêu cầu 2026-10-31

Ngoài Codex implement/integration, dùng Claude, Cursor/Grok và agy cho phần việc độc lập.
Không biến việc có nhiều provider thành nhiều writer cho cùng một file.

| Provider | Vai | Trạng thái thiết lập |
|---|---|---|
| Codex | Implement/integrate main product | Lane `product-integration`, worktree riêng |
| Claude | Review nội dung/claims/JTBD độc lập | `estagent-claude-review`, read-only tools; không Bash/Edit/Write |
| Cursor/Grok | Build nhỏ hoặc review nội dung | `grok-4.7-high` đã thấy trong Cursor catalog; checklist tại worktree `.worktrees/grok-content`, branch `review/grok-content` |
| agy | Review nội dung độc lập, không thấy review Claude trước khi nộp | User đã trust folder qua UI; `estagent-agy-review` đã nộp review baseline, chỉ đọc |

## Guardrails

- Tatejo giữ Git integration/commit/push; các reviewer không ghi repo, không git add/commit/push, không tạo metadata contributor/co-author.
- Không thêm `Co-Authored-By` cho Claude/Anthropic; giữ hook/checker hiện có. Khai báo AI hỗ trợ/source trong declaration vẫn trung thực.
- Reviewer chỉ đọc packet được giao: UI text và docs product/contract/context; không đọc env/auth/cookie/secret hoặc gửi ảnh người dùng ra provider.
- Grok build phải có output/path nhỏ rõ, worktree riêng và sandbox. Không đổi model nếu model được chỉ định không truy cập được; báo lỗi thật.
- Review chỉ nêu vấn đề có căn cứ và ảnh hưởng user; không tự xem proposal là tính năng đã triển khai hoặc claim Figma đã đọc khi chưa truy cập được.
- Chưa trust agy: không sửa settings/trust list tự động hoặc lách bằng chế độ bỏ quyền. Người dùng mở `agy` từ cwd project và xác nhận trust một lần, rồi Tatejo thử lại wrapper.
- Không chuyển conclusion của reviewer này cho reviewer khác trước handback độc lập. Tatejo kiểm nguồn và quyết định, không chuyển tiếp mù.
- Không mở thêm lane/sub-agent từ các lane này. Không merge build chỉ dựa trên báo cáo: phải xem diff và kiểm lại Acceptance.

## Task vòng đầu

- Claude: soát copy/JTBD renter shortlist, Creator/Viewer, lời hứa 3D/audio và mock/live; tối đa 5 findings có path/line, không ghi file.
- Grok: build duy nhất `docs/PRODUCT-ACCEPTANCE.md` trong worktree riêng, checklist manual/expected/evidence và tối đa 5 mâu thuẫn; chưa tích hợp vào main.
- agy sau trust: review cùng vấn đề nhưng trọng tâm clarity, evidence và nội dung gây hiểu sai; kết luận độc lập, không sửa source.
