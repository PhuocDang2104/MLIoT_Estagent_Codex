# Estagent — development preview

Repo: https://github.com/PhuocDang2104/MLIoT_Estagent_Codex

Hiện có frontend tĩnh EN/VI + motion và assistant intake FastAPI/LangGraph/SQLite.
Chưa có tour 3D end-to-end, Creator/Viewer hoàn chỉnh, audio tour hoặc tích hợp Maps/Supabase/GPU.

- **Teammate backend:** [bắt đầu ở đây](docs/BACKEND-HANDOFF.md), [rule agent backend](server/AGENTS.md).
- [API đang có và contract tour dự kiến](docs/CONTRACTS.md).
- Yêu cầu đã xác nhận: [hai view Tạo/Xem tour](docs/USER-VIEWS.md), [nhạc nền + lời từng khu](docs/TOUR-AUDIO.md), MVP không auth.
- [Thiết kế chat + gửi ảnh → tour như demo local](docs/CHAT-TO-TOUR.md): luồng Creator, nhánh panorama/ảnh thường, manifest và task liên lane.
- [Test local 0.2.0](docs/LOCAL-PREVIEW.md), [deploy runbook](docs/DEPLOYMENT.md).
- [Khai báo nguồn và thời gian build](docs/DECLARATION.md); [asset/license audit](web/evidence/ASSET-AUDIT.md).

Đọc `AGENTS.md` trước khi sửa. Không commit secret. Không thêm attribution Claude/Anthropic; khai báo AI hỗ trợ vẫn phải trung thực.
