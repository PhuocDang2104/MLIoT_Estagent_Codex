# Điều phối lane — 2026-10-31

Owner: Tatejo, phiên herdr `w6B:p1`. Repo chính: PhuocDang2104/MLIoT_Estagent_Codex.
Đây là phân công thực thi, không tuyên bố proposal đã được duyệt toàn bộ.
Chỉ đạo mới nhất của Thái: MVP chưa cần auth. Không tự mua dịch vụ/GPU hoặc thay đổi stack dùng chung.
Yêu cầu tour bổ sung đã xác nhận: nhạc nền + giọng giới thiệu từng khu; tiêu chí và ownership tại `docs/TOUR-AUDIO.md`. Xếp sau card đang chạy, chưa tự đổi contract.
Thái xác nhận hai view Tạo tour và Xem tour; ngữ cảnh, ranh giới và Acceptance tại `docs/USER-VIEWS.md`. MVP không cần auth, không gộp Creator intake với Viewer Q&A.

| Lane/pane | Phạm vi ghi độc quyền trong vòng này | Deliverable / nghiệm thu | Trạng thái giao |
|---|---|---|---|
| Frontend `w6D:p1` | `web/` trừ `web/assistant.*`; không ghi build/package sau khi bàn giao | Hoàn thành EN/VI đang được Thái giao + motion; kiểm browser, reduced motion, regression; kê source ảnh/font và đề xuất thay nếu license chưa rõ | Gửi bổ sung sau task đang chạy |
| Chatbot `w6E:p1` | `server/assistant/`, `tests/ai/`, `web/assistant.*`, `docs/ASSISTANT.md`, `docs/INTEGRATIONS.md`, `.env.example` | Nối luồng assistant local, xác minh backend lưu/khôi phục hồ sơ và browser; tách mock/live; giữ key ngoài log, không thêm auth | Giao vòng 1 |
| Deploy `w6F:p1` | `deploy/`, `docs/DEPLOYMENT.md`, `status/web.md` | Chuẩn bị backend release độc lập và endpoint/proxy proposal; xác minh dependency/health local khi có thể; báo đúng blocker GitHub App; không tự dựng Supabase/đổi stack hoặc deploy bản dirty | Giao vòng 1 |
| Product Integration `w6G:p1` | `.worktrees/product-sync`, nhánh `integration/product-sync`; scope liên lane theo `docs/PRODUCT-INTEGRATION.md` | Nối sản phẩm same-origin, Creator→draft/preview→publish→Viewer, UI/API/audio thống nhất, browser/tests + handback | Thay task core xếp hàng; đã giao triển khai |
| Điều phối `w6B:p1` | File plan/contract/fixture, root scripts nếu cần | Hợp nhất đề xuất MVP/contract; review độc lập trước commit tích hợp; không sửa vùng đang có owner | Đang điều phối |

## Luật bàn giao

- Các pane hiện cùng checkout: không `git add .`, không commit/push/merge/rewrite hoặc stash thay đổi chung; Tatejo là writer duy nhất cho Git state.
- Không sửa file ngoài vùng ghi. Nếu cần dependency/build/root/contract thì trả `NEED` cùng patch đề xuất; không tự sửa.
- Ưu tiên yêu cầu trực tiếp mới nhất của Thái. Nếu có xung đột với brief điều phối, giữ yêu cầu của Thái và báo lại.
- Không tạo thêm pane/subagent. Hai task mới hoạt động đồng thời; core chỉ bắt đầu sau handback của một task vòng 1.
- Timebox mỗi card 45 phút, tối đa hai hướng sửa. Report theo AGENTS: STATUS/CHANGED/EVIDENCE/NEED/CONTRACT_CHANGE/NOTES; ghi source và fixture/live.
- Handback không đồng nghĩa nghiệm thu. Tatejo tự chạy lại gate và xem browser/output phù hợp; thiếu schema/core không được báo strict xanh.
- Mốc H0, phạm vi sản phẩm cuối và contract còn cần chốt; không tự thay kiến trúc theo một trong hai proposal mâu thuẫn.

## Thứ tự tích hợp

1. Frontend bàn giao file/build và bằng chứng; chatbot xác nhận endpoint local ổn định.
2. Core kiểm chứng tính khả thi; Tatejo hợp nhất plan/contract/fixture dựa trên dữ kiện và quyền đã có.
3. Deploy nhận commit đã nghiệm thu, nối FE–BE theo endpoint đã xác định; API live chỉ chạy khi có budget và quyền dữ liệu rõ.
4. Smoke e2e, declaration/license, attribution check rồi mới commit/push/deploy trong phạm vi được giao.
