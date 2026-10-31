<div align="center">

<img src="../web/assets/favicon.svg" width="64" height="64" alt="Biểu tượng Estagent" />

# Estagent

### See the space. Understand the place.

**Hiểu không gian trước khi quyết định đi xem nhà.**

<p><a href="https://estagent.duckdns.org">Trải nghiệm demo</a> · <a href="../README.md">README</a> · <a href="Business%20Workflow%20Langgraph/Estagent_Business_LangGraph_Flow.md">Luồng LangGraph</a> · <a href="DEPLOYMENT.md">Triển khai</a></p>

</div>

---

## Khi ảnh đẹp vẫn chưa đủ

Một listing có nhiều ảnh vẫn có thể để lại những câu hỏi rất thực tế: đây là phòng
nào, các khu liên hệ với nhau ra sao, góc chưa chụp có gì, và thông tin nào đã được
chủ nhà xác nhận? Người tìm thuê phải tự ghép các mảnh thông tin trước khi chọn
những căn đáng dành thời gian đến xem.

**Estagent kết nối hình ảnh, mô hình không gian, lời giới thiệu và hội thoại trong
cùng một trải nghiệm tham quan.** Chủ nhà hoặc môi giới cung cấp dữ liệu và duyệt
nội dung. Người xem khám phá tour đã xuất bản, hỏi theo khu đang xem và nhận câu
trả lời trong phạm vi bằng chứng được cung cấp.

Sản phẩm hướng đến việc hỗ trợ lựa chọn và chuẩn bị buổi xem nhà. Hiệu quả giảm
số lần đi xem hoặc cải thiện quyết định vẫn cần được đánh giá với người dùng và
dữ liệu bất động sản được phép sử dụng.

## Hai trải nghiệm, một nguồn thông tin đã duyệt

| | Creator / Business | Viewer / Người tìm thuê |
| :--- | :--- | :--- |
| **Mục tiêu** | Tạo và giải thích bất động sản bằng một tour có thể chỉnh sửa | Hiểu căn nhà để quyết định có muốn đi xem trực tiếp |
| **Đầu vào** | Ảnh, panorama, mô tả và mặt bằng nếu có | Tour được chia sẻ, khu đang xem và câu hỏi |
| **Trải nghiệm** | AI đề xuất bố cục; người tạo làm rõ, xem mô hình, duyệt lời giới thiệu và xuất bản | Xem dollhouse, vào panorama, nghe hướng dẫn và trò chuyện |
| **Quyền kiểm soát** | Quản lý bản nháp và phê duyệt phiên bản xuất bản | Đọc thông tin đã duyệt và thực hiện điều hướng được hỗ trợ |

Bản nháp và bản xuất bản có vòng đời riêng. Chỉnh sửa về sau tạo một phiên bản
làm việc mới trong Studio; tour đã chia sẻ giữ nguyên nội dung của snapshot đó.
MVP phân tách dữ liệu Creator bằng phiên cookie, chưa phải hệ thống tài khoản.

## Một hành trình từ tư liệu đến tour

### 1. Cung cấp bối cảnh

Creator tải ảnh hoặc panorama, thêm mô tả bất động sản và mặt bằng nếu có.
Studio hỗ trợ tối đa 12 captures cho một project. Hệ thống kiểm định ảnh, xử lý
metadata của upload mới và lưu dữ liệu riêng tư. Một ảnh chỉ được coi là panorama
khi có xác nhận và điều kiện định dạng phù hợp.

### 2. Làm rõ không gian

OpenAI phân tích hình ảnh và mô tả để tạo scene plan có cấu trúc, nhóm captures
theo phòng và nêu thông tin cần làm rõ. Creator có thể trả lời câu hỏi, yêu cầu
sửa kế hoạch rồi duyệt bố cục. Khi thiếu số đo, layout phải được ghi rõ là xấp xỉ.

Blender nhận scene plan đã được kiểm tra để dựng mô hình có vật liệu, openings,
fixtures được hỗ trợ và vị trí checkpoint. Three.js hiển thị dollhouse trong
Studio và Viewer. Runtime hiện hỗ trợ mô hình được author theo một tầng;
đây không phải tái dựng đo đạc bằng photogrammetry hoặc Gaussian Splatting.

### 3. Biên tập câu chuyện của căn nhà

Hệ thống ghép nội dung với checkpoint, tạo đường tham quan và soạn lời giới thiệu.
Creator duyệt nội dung trước khi tạo giọng đọc OpenAI TTS. Nhạc nền và audio được
cung cấp phải có nguồn/quyền sử dụng theo luồng tương ứng.

Với chat chỉnh sửa, người dùng mô tả điều muốn thay đổi bằng ngôn ngữ tự nhiên.
Backend kiểm đề xuất, hiển thị thay đổi để xác nhận rồi tạo generation mới.
LangGraph chạy lại các bước chịu ảnh hưởng; phần đã hoàn thành có thể được giữ
lại, bao gồm audio có checkpoint và nội dung khớp chính xác.

### 4. Xuất bản và khám phá

Sau khi đủ điều kiện và được duyệt, hệ thống tạo một published snapshot.
Người xem chuyển giữa dollhouse và panorama, chọn khu, phát/tạm dừng lời hướng
dẫn, điều chỉnh audio và hỏi về thông tin trong tour. Các luồng export hiện có
phụ thuộc loại tour, quyền sở hữu và renderer đã bật; MP4 của photo/panorama tour
không được mô tả như video render điện ảnh từ ngôi nhà 3D.

## Kiến trúc AI tạo tour

[![Sơ đồ OpenAI và LangGraph cho luồng tạo tour bất động sản](Langgraph%20Tour%20Generation%20OpenAI%20Architecture.png)](Langgraph%20Tour%20Generation%20OpenAI%20Architecture.png)

<p align="center"><sub>Ảnh kiến trúc do người dùng cung cấp. Nhấn vào hình để xem bản đầy đủ.</sub></p>

Sơ đồ mô tả hướng sản phẩm: chuẩn hóa đầu vào, hiểu scene, tổ chức spatial graph,
dựng mô hình, gắn checkpoint, tạo narration/navigation rồi đóng gói kết quả.
Các nhãn model và điểm đánh giá trong hình thể hiện phân vai thiết kế; cấu hình
API thực tế nằm ở backend và được quản lý theo từng vai trò.

Trong runtime hiện tại, LangGraph lưu checkpoint và điều phối các bước có duyệt.
Một SQLite outbox giữ lệnh chạy bền vững; request ID, revision và quan hệ phiên bản
giúp xử lý retry và chỉnh sửa. Blender được gọi qua worker CLI có giới hạn, sử
dụng scene data đã validate. Điểm nối worker HTTP cũng được giữ lại để tích hợp
dịch vụ geometry riêng. Blender MCP chưa phải đường thực thi mặc định.

[Xem graph thực thi và Mermaid](Business%20Workflow%20Langgraph/Estagent_Business_LangGraph_Flow.md) ·
[Chi tiết house-modeling agent](HOUSE-MODELING-AGENT.md)

## Trợ lý hiểu bối cảnh đang xem

[![Sơ đồ trợ lý khách hàng với spatial context và kiến trúc RAG](Langgraph%20Rag%20Spatial%20Context%20Assistant.png)](Langgraph%20Rag%20Spatial%20Context%20Assistant.png)

<p align="center"><sub>Kiến trúc đích cho truy xuất và điều phối công cụ; không phải danh sách tích hợp đã bật.</sub></p>

Trợ lý được thiết kế để gắn câu hỏi với khu người dùng đang xem, thông tin đã duyệt
và hội thoại liên quan. Khi có đủ bằng chứng, trợ lý trả lời hoặc đề nghị một thao
tác Viewer được hỗ trợ. Khi chưa đủ, câu trả lời cần nêu giới hạn và làm rõ câu hỏi.

| Câu hỏi | Cách hỗ trợ |
| :--- | :--- |
| “Tôi đang ở khu nào?” | Dùng scene/checkpoint đang được chọn |
| “Phòng này có những tiện nghi gì?” | Trả lời từ thông tin và nội dung đã duyệt trong tour |
| “Đưa tôi đến phòng ngủ.” | Đề xuất checkpoint hợp lệ; backend kiểm target trước khi điều hướng |
| “Tủ rộng 1,8 m có vừa không?” | Cần số đo đáng tin cậy; mô hình xấp xỉ không đủ để khẳng định |

Runtime hiện có Q&A theo tour, scene/checkpoint và ngữ cảnh hội thoại có giới hạn.
Viewer không được thay metadata nguồn hoặc tự xuất bản. Các câu hỏi về hướng nhìn
chi tiết, object grounding, tiện ích lân cận hay thị trường là phần mở rộng cần
spatial context và nguồn dữ liệu tương ứng.

Sơ đồ RAG định hướng bổ sung Knowledge Hub, PostgreSQL, hybrid BM25/semantic
retrieval, spatial query và các connector Maps/Places/Market Data. Những thành
phần này chưa được trình bày như kết nối đang chạy trên main.

## Những gì đã có và phần tiếp theo

| Năng lực | Trạng thái trong sản phẩm |
| :--- | :--- |
| OpenAI cho modeling, vision, text, TTS và trợ lý | Đã có tích hợp backend theo vai trò; key không đưa xuống trình duyệt |
| Scene planning, clarification và duyệt layout | Đã có trong Studio |
| Mô hình một tầng bằng Blender và dollhouse/panorama bằng Three.js | Đã có; layout/scale có thể mang tính xấp xỉ |
| Chat chỉnh sửa, generation history và published snapshots | Đã có |
| Guided audio và Q&A theo khu đang xem | Đã có theo khả năng của từng luồng tour |
| Media riêng tư, quota và export | Có adapter local/MinIO và các tính năng bật theo cấu hình |
| Hybrid RAG, PostgreSQL knowledge hub, Maps và market intelligence | Hướng phát triển |
| Tái dựng metric, nhiều tầng và 3D cinematic export tổng quát | Chưa phải năng lực đã được chứng minh của runtime hiện tại |

Các bài kiểm tra provider connectivity, Blender và browser đã được ghi tại
[release Studio + Seoul](STUDIO-SEOUL-RELEASE.md). Chúng không thay thế việc đánh
giá chất lượng tự động dựng một căn nhà đầy đủ bằng dữ liệu thực.

## Chạy và đọc tiếp

```bash
bash scripts/dev.sh
```

Chạy lệnh từ root repo với Python 3.13, uv và Bash; mở `http://127.0.0.1:5180/`.
Photo-tour editor ở `/business/photos` hỗ trợ thử visual flow không cần LLM.
Studio ở `/business/create` cần cấu hình OpenAI và geometry worker khi bắt đầu
generation. Script không tự đọc `.env`; model, giới hạn và feature flags theo
backend environment. Các hành động generation/chat/narration khi được bật có
thể gọi API có phí.

- **Phát triển:** [README](../README.md), [user views](USER-VIEWS.md), [API contracts](CONTRACTS.md).
- **Runtime:** [Studio runtime](STUDIO-RUNTIME.md), [house modeling](HOUSE-MODELING-AGENT.md), [chat context](CHAT-FLOW-HANDOFF.md).
- **Vận hành:** [deployment](DEPLOYMENT.md), [SSH/deploy](STUDIO-DEPLOY.md), [MinIO](MINIO-INTEGRATION-HANDOFF.md), [rollback](ROLLBACK-SAFETY.md).
- **Nguồn và tài sản:** [declaration](DECLARATION.md), [asset sources](../web/assets/SOURCES.md).

<details>
<summary><strong>Ghi chú biên tập và nguồn hình</strong></summary>

Hai sơ đồ PNG được người dùng cung cấp và giữ nguyên nội dung. Phần giới thiệu
được viết từ user views, runtime, house-modeling và release handoff trong repo.
Tài liệu [product context](PRODUCT-CONTEXT.md) giải thích vấn đề/JTBD ban đầu;
[Product Proposal](../Product%20Proposal.md) giữ hướng đề xuất rộng hơn.

Bố cục tham khảo cách tổ chức hero, điều hướng, tính năng và quick start của
[Dify](https://github.com/langgenius/dify) và [Supabase](https://github.com/supabase/supabase),
cùng [hướng dẫn README của GitHub](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes).
Nội dung sản phẩm được viết mới; không sao chép prose, logo hoặc cover của các repo đó.

</details>
