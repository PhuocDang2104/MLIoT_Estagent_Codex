# API bên thứ ba cho Estagent

Ngày khảo sát: 2026-10-31. Phạm vi: chatbot text/voice, LangGraph thu thập thông tin, tour bất động sản từ ảnh panorama, tìm tiện ích xung quanh, lưu trữ và xuất bản tour.

**Trạng thái thực tế:** backend assistant đã có code gọi OpenAI; chưa xác minh bằng key thật. Các biến mới trong `.env.example` chỉ chuẩn bị cấu hình, chưa có adapter cho Maps, Apify, Supabase, RunPod hay email. Điền key không tự kích hoạt các tính năng này. Chưa tạo tài khoản, triển khai dịch vụ hoặc chạy tác vụ tính phí trong đợt khảo sát này.

**Quyết định của Thái:** MVP hiện tại không cần auth: không triển khai đăng nhập, đăng ký, OTP, magic link hoặc email xác thực. Supabase chỉ dùng cho database/storage; Auth và Resend để giai đoạn sau.

## Chọn dịch vụ theo tính năng

| Ưu tiên | Dịch vụ | Tính năng / lý do chọn | Cấu hình |
| --- | --- | --- | --- |
| Hiện có | OpenAI | Hiểu ngôn ngữ, vision, hội thoại và giọng nói; dùng lại key đã có | `OPENAI_API_KEY` |
| P0 | Google Maps Platform | Địa chỉ → tọa độ, tìm trường/bệnh viện/siêu thị, tính quãng đường và thời gian di chuyển | `GOOGLE_MAPS_SERVER_KEY`; thêm `GOOGLE_MAPS_BROWSER_KEY` nếu nhúng bản đồ |
| P0 | Supabase self-host | Postgres và Storage cho hồ sơ bất động sản, ảnh và tour; giữ quyết định dùng VM hiện tại | `SUPABASE_URL`, key backend phù hợp phiên bản; bucket |
| Có điều kiện | RunPod Serverless | GPU chạy PanSplat khi máy/local/Kaggle không đáp ứng | `RUNPOD_API_KEY`, `RUNPOD_ENDPOINT_ID` |
| P1 | Apify | Thu thập danh sách địa điểm chạy nền, phục vụ khảo sát/kho dữ liệu | `APIFY_API_TOKEN` |
| Để sau, ngoài MVP | Resend | Email xác nhận, khôi phục tài khoản, magic link qua SMTP của Supabase | `RESEND_API_KEY`, `EMAIL_FROM` |
| Tùy chọn cho dev | LangSmith | Trace các bước LangGraph để tìm lỗi và đánh giá agent | `LANGSMITH_API_KEY`, `LANGSMITH_TRACING`, `LANGSMITH_PROJECT` |

## Lấy cấu hình và chuẩn bị tích hợp

### Google Maps

1. Tạo/chọn Google Cloud project, bật billing và các API cần dùng trong [Google Maps Console](https://console.cloud.google.com/google/maps-apis/credentials).
2. Key backend: bật và giới hạn quyền theo Places API (New), Geocoding API và Routes API. Với backend có IP cố định, thêm hạn chế theo IP.
3. Nếu cần hiển thị bản đồ Google trong viewer: tạo key riêng cho Maps JavaScript API, hạn chế HTTP referrer theo domain deploy và localhost cần dùng. Key browser là công khai theo thiết kế, không được dùng thay key backend.
4. Adapter dự kiến: geocode địa chỉ → Nearby Search theo tọa độ/loại tiện ích → Routes cho các địa điểm người dùng chọn. Chỉ yêu cầu các trường cần thiết qua field mask; ghi rõ phương tiện khi trình bày thời gian di chuyển.

Nguồn: [lấy key](https://developers.google.com/maps/documentation/places/web-service/get-api-key), [bảo vệ key](https://developers.google.com/maps/api-security-best-practices), [Nearby Search](https://developers.google.com/maps/documentation/places/web-service/nearby-search), [Routes](https://developers.google.com/maps/documentation/routes/compute_route_directions). Phí phụ thuộc API/SKU và trường dữ liệu yêu cầu; kiểm tra [bảng SKU](https://developers.google.com/maps/billing-and-pricing/sku-details) trước khi bật billing cho môi trường thật. Hiển thị attribution theo tài liệu API khi trình bày kết quả.

### Supabase self-host

Dự án đã chọn VM + Supabase self-host. Cần dựng **stack Estagent riêng** trước khi có URL/key; không lấy key từ các stack dự án khác trên VM. Chưa cần mua thêm Firebase, Auth0 hoặc dịch vụ object storage riêng cho MVP.

- Backend dùng `SUPABASE_SECRET_KEY` trên bản hỗ trợ key mới. `SUPABASE_PUBLISHABLE_KEY` chưa cần cho luồng MVP truy cập storage qua backend.
- Bản dùng legacy JWT keys: backend dùng `SUPABASE_SERVICE_ROLE_KEY` trong dòng chú thích của template. Chưa cần `SUPABASE_ANON_KEY`; không bắt buộc điền cả hai thế hệ key.
- Secret/service-role chỉ ở backend. Không đưa key đặc quyền vào frontend dù MVP không có đăng nhập.
- Tạo bucket private `estagent-assets`; backend quản lý upload và cấp URL ký có hạn cho viewer. MVP chưa thiết kế policy theo tài khoản người dùng, không mở quyền ghi public để bỏ qua Auth.
- `DATABASE_URL` dành cho kết nối Postgres trực tiếp khi chuyển checkpoint LangGraph khỏi SQLite. `REDIS_URL` dành cho queue worker nếu triển khai; cả hai chưa được assistant hiện tại sử dụng.

Nguồn: [key cho self-host](https://supabase.com/docs/guides/self-hosting/self-hosted-auth-keys), [Storage access control](https://supabase.com/docs/guides/storage/security/access-control). Chi phí ở hướng self-host là VM, lưu trữ, backup và vận hành; không tự động phát sinh một gói Supabase Cloud.

### RunPod cho PanSplat

Lấy key trong tài khoản theo [hướng dẫn credentials](https://docs.runpod.io/get-started/credentials). Sau đó dựng container GPU chứa code/model/checkpoint PanSplat được phép sử dụng, triển khai endpoint rồi điền endpoint ID. **RunPod không cung cấp sẵn API tái dựng PanSplat chỉ bằng việc tạo key.**

Worker nhận tham chiếu ảnh trong storage và trả tham chiếu asset theo contract dự án. Backend gửi `/run`, lưu job ID, theo dõi `/status/{id}`; lưu kết quả bền vững vào storage. Không giữ asset chỉ trong filesystem tạm của worker. Không tự gửi lại job khi request timeout mà chưa đối soát trạng thái, tránh chạy trùng. Xem [API tác vụ bất đồng bộ](https://docs.runpod.io/serverless/endpoints/send-requests). Chọn GPU và giới hạn thời gian trước mỗi đợt thử có phí; chưa có cấu hình phần cứng để báo một mức giá cố định.

### Apify cho thu thập chạy nền

Token lấy tại [Apify API & Integrations](https://console.apify.com/settings/integrations). Actor dự kiến: [`compass/crawler-google-places`](https://apify.com/compass/crawler-google-places). Gửi Bearer token ở backend theo [Apify API](https://docs.apify.com/integrations/api), lưu run ID và dataset ID để theo dõi tiến độ.

Trước lần chạy có phí phải hiển thị phạm vi, các add-on và chi phí dự kiến theo gói hiện hành. Giới hạn `maxCrawledPlacesPerSearch` áp dụng theo từng từ khóa, không phải tổng toàn bộ job. Nhu cầu tiện ích quanh nhà chưa cần thu thập reviewer, nhân sự hoặc enrichment liên hệ. Apify không thay thế Routes để tính thời gian đi đường.

### Resend và LangSmith

- **Resend — để sau, không cần tạo key cho MVP:** khi có yêu cầu email, tạo key, xác minh domain gửi mail rồi cấu hình [Supabase custom SMTP](https://resend.com/docs/send-with-supabase-smtp). `RESEND_API_KEY` có thể dùng làm mật khẩu SMTP theo hướng dẫn; `EMAIL_FROM` cần thuộc domain đã xác minh. Các biến trong app chưa tự cấu hình SMTP cho stack Supabase. Chỉ cần thực hiện khi triển khai luồng email Auth hoặc email giao dịch.
- **LangSmith:** tạo key và project theo [observability quickstart](https://docs.langchain.com/langsmith/observability-quickstart). Giữ `LANGSMITH_TRACING=false` mặc định; chỉ bật sau khi chọn dữ liệu nào được gửi vào trace. LangGraph local không cần LangSmith key. Chưa kiểm tra kết nối tracing thực tế.

## Phần chưa cần thêm API key

- LangGraph, SQLite, Three.js, Blender và FFmpeg có thể chạy như thư viện/công cụ cục bộ. Không cần đăng ký một SaaS cho mỗi thành phần.
- OpenAI đã bao phủ tiếng nói cho hướng triển khai hiện tại; chưa có nhu cầu thêm ElevenLabs hoặc một nhà cung cấp LLM khác.
- Chưa xác minh được nguồn API giá giao dịch bất động sản Việt Nam phù hợp cùng quyền sử dụng và endpoint cụ thể. Không tạo `MARKET_API_KEY` giả định. P2 cần chọn đối tác dữ liệu trước; demo có thể dùng dataset có quyền sử dụng và ghi rõ nguồn/ngày, phân biệt giá rao với giá giao dịch.

## Thứ tự triển khai tiếp

1. Điền key OpenAI hiện có, kiểm tra chat/voice thật theo `docs/ASSISTANT.md`.
2. Nối Maps vào tool backend của agent; để LangGraph hỏi rõ địa chỉ khi còn mơ hồ trước khi geocode/tìm tiện ích.
3. Dựng Supabase Estagent, migration rồi nối upload/lưu kết quả qua backend; không triển khai Auth trong MVP.
4. Nếu thiếu GPU, triển khai PanSplat worker lên RunPod sau khi xác minh model và contract đầu ra.
5. Thêm Apify và tracing theo nhu cầu demo; email để giai đoạn sau. Các tác vụ mất nhiều thời gian cần trả job ID/progress; không giữ một request chat chờ toàn bộ job.

Khai báo nguồn: tài liệu/configuration được soạn với Codex ngày 2026-10-31, dựa trên proposal và tài liệu chính thức dẫn ở trên. Đây là chuẩn bị tích hợp, không phải bằng chứng đã chạy dịch vụ hoặc đã hoàn thành build trong thời gian thi; H0 chưa được xác minh.
