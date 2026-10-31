# Independent content review — 2026-10-31

Claude và agy review độc lập baseline MAIN trước tích hợp, chỉ đọc; không ghi source hoặc Git metadata.
Cursor/Grok build checklist trong worktree riêng; Tatejo đọc lại trước khi đưa vào repo.
Đây là review tĩnh nội dung, không phải nghiệm thu browser hay chứng nhận bản tích hợp hiện tại.

## Findings dùng để đối chiếu bản tích hợp

1. Primary user phải nhất quán là rental seeker shortlist trước chuyến xem nhà; buyer là vision, không tự mở scope MVP.
2. Landing/navigation cần entry riêng Creator và Viewer, rõ create → preview/review → publish → view.
3. Panorama checkpoint không được quảng bá như reconstruction 3D/đủ 360°/đo đạc hoặc quan hệ phòng đã xác minh.
4. UI phải thống nhất nơi lưu dữ liệu, trạng thái AI thật/keyless và EN/VI; intake cũ rời rạc không nên là luồng chính.
5. Lời/audio/Q&A có nguồn, không bịa kích thước/fit; nhạc/lời không chồng chatbot, thiếu audio phải nói thiếu.

## Tatejo kiểm lại nhận xét reviewer

- Ký hiệu `narration.lines[].room` không xuất hiện nguyên văn không chứng minh thiếu field: legacy JSON đã có `room` bên trong `lines`; sửa nhận xét Grok trong checklist.
- Không coi keyless là mock thành công. Runtime phải báo thiếu cấu hình; fixture provider chỉ ở tests.
- Không gọi panorama coverage thiếu là 360° hoàn chỉnh dù một reviewer dùng chữ checkpoint 360°.
- Findings trên main cũ phải so với source và evidence của nhánh mới, không mặc định còn tồn tại.
- Figma chưa truy cập được; không reviewer nào được claim đã apply hoặc kiểm wireframe.

Bản tích hợp được kiểm riêng bằng gate, browser flow/restart/dynamic counts và documented dev-command.
Giới hạn core/audio/OpenAI live phải giữ trong handoff và release notes. Không thay author/co-author để che AI hỗ trợ; khai báo nguồn vẫn giữ.

## Đóng vòng review

Thái yêu cầu đọc và gỡ pane review: đã thu câu trả lời cuối của Claude và đủ 5 findings/5 Acceptance của agy trước khi đóng.
Hai review đều trên baseline cũ; bản tích hợp đã chỉnh renter copy, tách entry Creator/Viewer,
ghi đúng panorama và lưu server, giữ keyless503, rồi được kiểm browser và deploy preview riêng.
Nhạc/narration thật, core và OpenAI live vẫn mở; không coi việc đóng reviewer là các hạng mục đó đã xong.
Không ai trong hai reviewer ghi source/commit/co-author metadata. Chỉ đóng pane Claude/agy do Tatejo mở, không đóng pane build hoặc pane người dùng.
