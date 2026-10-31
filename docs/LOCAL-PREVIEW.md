# Local preview 0.2.0 — 2026-10-31

Bản tích hợp frontend EN/VI, motion và assistant intake. Không phải bản hoàn tất tour end-to-end.

## Đường dẫn test

- Landing: http://127.0.0.1:5190/
- Workspace nhập liệu/ảnh: http://127.0.0.1:5190/experience.html
- Assistant qua backend: http://127.0.0.1:5191/assistant.html

Frontend tĩnh không proxy API; mở assistant qua cổng backend 5191. Không mở assistant.html từ cổng 5190 để kiểm AI.
Nếu đã có key hợp lệ trong `.env.local`, thao tác chat/micro của người test có thể gọi API tính phí.
Không có key thì assistant hiện trạng thái chưa kết nối; không tạo câu trả lời giả.

## Chạy lại

Từ gốc repo, terminal thứ nhất:

```bash
npm --prefix web run build
python3 -m http.server 5190 --bind 127.0.0.1 --directory web/dist
```

Terminal thứ hai (cần uv và dependencies backend):

```bash
ASSISTANT_ORIGIN=http://127.0.0.1:5191 uv run --python 3.13 \
  --with-requirements server/assistant/requirements.txt \
  python -m uvicorn server.assistant.app:app --env-file .env.local \
  --host 127.0.0.1 --port 5191
```

Chưa có `.env.local` thì bỏ `--env-file .env.local` để kiểm trạng thái thiếu key. Dừng từng server bằng Ctrl+C.

## Kiểm thử thủ công

1. Đổi EN/VI trên landing, mở workspace trong tab khác, kiểm đồng bộ ngôn ngữ và font tiếng Việt.
2. Kiểm motion, bật Reduced Motion, resize mobile, upload/xem/xóa ảnh và nhập metadata.
3. Assistant: nhập thông tin, bỏ qua mục tùy chọn, xác nhận, sửa rồi reload kiểm giữ hồ sơ; chat/micro live phụ thuộc key/model/quota.

## Chưa có trong bản này

- Hai view Creator/Viewer hoàn chỉnh, tạo/publish tour, viewer 3D và spatial Q&A.
- Nhạc nền và narration từng khu; đây mới là yêu cầu/backlog trong TOUR-AUDIO.md.
- Core reconstruction và fixture/schema tour, nên chưa đạt strict gate end-to-end.
- Chưa kiểm OpenAI live hoặc deploy production trong vòng preview này.
- Hero lấy từ reference vẫn chưa xác minh quyền dùng; xem web/evidence/ASSET-AUDIT.md trước khi phát hành công khai.

Source/declaration chi tiết ở docs/ASSISTANT.md và web/evidence/HANDOFF-FRONTEND.md; H0 chưa xác minh.

## Kết quả kiểm bản tích hợp

- Gate thường: web lint/test/build và AI compile/pytest PASS; core và tour contract SKIP, không claim strict xanh.
- HTTP 200 ở landing/workspace cổng 5190 và assistant cổng 5191.
- Browser Chromium: VI, locale khi chuyển workspace, mobile 390px không tràn ngang, mở assistant không có JS pageerror: PASS.
- Lần browser đầu click trước khi script defer sẵn sàng; kiểm lại sau load/network-idle và chờ locale cập nhật: PASS.
- GET trạng thái backend: `configured=false` tại lúc bàn giao, chưa có chat/voice live; không gửi request model trong smoke.
- Chưa đưa phần deploy/ và thay đổi runbook/status deployment đang được lane khác thực hiện vào snapshot này.
