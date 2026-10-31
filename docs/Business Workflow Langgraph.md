# **ESTAGENT — Business AI Tour Builder**

**LangGraph-Based Technical Proposal \| Version 1.0**

## **1\. Objective**

Xây dựng một workflow tự động chuyển đổi ảnh panorama 360° và thông tin bất động sản thành **Intelligent 3D Property Tour** có khả năng khám phá, hiểu ngữ cảnh không gian, thuyết minh bằng AI và xuất bản đa định dạng.

**Core workflow:**

Business Upload → Input Validation → Parallel Semantic & Spatial Processing → Spatial Knowledge Fusion → Guided Tour Generation → Quality Validation → Business Review → Publish / Export.

Toàn bộ pipeline do **một LangGraph StateGraph** điều phối, kết hợp các AI models, reconstruction workers và Blender MCP. Business có thể can thiệp, chỉnh sửa và chạy lại từng công đoạn khi cần.

## **2\. Input Specification**

| Input | Requirement |
| ----- | ----- |
| 360° Panoramas | Bắt buộc. Ảnh equirectangular, ưu tiên nhiều góc chụp có overlap, được nhóm theo phòng |
| Property Description | Bắt buộc. Mô tả bất động sản bằng ngôn ngữ tự nhiên |
| Property Metadata | Tùy chọn. Giá, diện tích, số phòng, tiện nghi, thông số, địa chỉ |
| Floorplan | Tùy chọn. Bản vẽ 2D, sơ đồ phòng hoặc floorplan có kích thước |
| Camera Information | Tùy chọn. Vị trí, thứ tự ảnh, hướng chụp, chiều cao camera |

Trước khi chạy pipeline, hệ thống kiểm tra định dạng, chất lượng, độ phủ ảnh và dữ liệu đầu vào. Các phòng thiếu góc chụp hoặc không có đủ overlap được đánh dấu để Business bổ sung.

## **3\. LangGraph Processing Nodes**

| Node | Processing Logic | Output |
| ----- | ----- | ----- |
| **N1. Input Analyzer** | Validate panorama, đọc description, trích xuất metadata và phân loại dữ liệu đầu vào | Normalized Property Data |
| **N2. Scene Understanding** | GPT Vision phân tích từng panorama: room type, nội thất, cửa, cửa sổ, đặc điểm quan sát được | Per-Panorama Semantic Records |
| **N3. Spatial Estimation** | Ước lượng camera poses, room connectivity; căn chỉnh floorplan có sẵn hoặc suy luận layout sơ bộ | Camera Pose Graph \+ Draft Layout |
| **N4. 3D Reconstruction** | Gọi PanSplat worker tái dựng các vùng 3D từ panorama phù hợp, căn chỉnh trong hệ tọa độ chung | Registered Gaussian Scenes |
| **N5. Blender Spatial Builder** | Dựng/hiệu chỉnh floorplan geometry, room boundaries, checkpoint anchors và navigation proxy qua Blender MCP | Spatial Geometry \+ Navigation Graph |
| **N6. Semantic Grounding** | Matching room/checkpoint với description, metadata, panorama observations và global 3D coordinates | Enriched Checkpoint Knowledge |
| **N7. Tour Generator** | Lập tour sequence, tạo narration scripts, gọi TTS, thiết lập camera keyframes và timing | Guided Tour Package |
| **N8. Quality Validator** | Kiểm tra factual consistency, scene alignment, navigation, checkpoint coverage và unsupported claims | QA Report \+ Review Flags |
| **N9. Business Approval** | Tạm dừng workflow để Business xem trước, chỉnh sửa hoặc phê duyệt | Approved Tour Version |
| **N10. Publisher** | Đóng gói asset và kích hoạt website publishing hoặc video rendering | Published Tour / MP4 |

Các node N2 và N3 có thể xử lý song song. PanSplat chạy bằng GPU worker riêng; Blender chạy bằng spatial worker riêng. LangGraph chỉ lưu trạng thái, nhận kết quả và điều phối các bước tiếp theo.

## **4\. Reconstruction & Blender MCP Strategy**

### **4.1. PanSplat Reconstruction**

* Ước lượng và chuẩn hóa camera poses giữa các panorama.  
* Chọn các cặp panorama phù hợp theo room/region và độ chồng lấp.  
* Chạy pretrained PanSplat để tổng hợp các vùng Gaussian 3D.  
* Căn chỉnh các vùng reconstruction vào global coordinate system.  
* Đánh giá chất lượng vùng được dựng và khả năng xuất asset tương thích web viewer.

PanSplat không trực tiếp cung cấp floorplan chính xác, collision mesh hay khả năng tự dựng mọi phòng. Những thành phần này phải được xử lý bổ sung.

### **4.2. Floorplan & Spatial Geometry**

**Khi có floorplan:** Phân tích room boundaries, wall geometry, doors và liên kết floorplan với camera positions. Những thông số có kích thước đáng tin cậy được sử dụng để hiệu chỉnh tỉ lệ.

**Khi không có floorplan:** Sử dụng panorama layout estimation, depth/structural cues và room connectivity để suy luận sơ đồ không gian sơ bộ. Blender tạo floorplan draft và proxy geometry dựa trên kết quả này.

Floorplan suy luận phải được đánh dấu là *AI-estimated*, không được mặc định là bản vẽ đo đạc chính xác.

### **4.3. Blender MCP Responsibilities**

Blender MCP được dùng để yêu cầu Blender:

* Tạo và hiệu chỉnh room polygons, floor, wall, ceiling và door openings.  
* Đặt camera/checkpoint anchors theo tọa độ đã đăng ký.  
* Xây dựng collision geometry, walkable regions và navigation constraints.  
* Tạo các camera paths, kiểm tra vị trí và xuất spatial assets cho viewer.

**Vai trò chính:** xây dựng lớp hình học và điều hướng phục vụ Gaussian scene, không thay thế Gaussian reconstruction.

Trong production, chỉ cho phép các thao tác Blender được kiểm soát qua một tool wrapper; không để nội dung người dùng trực tiếp kích hoạt Blender Python tùy ý.

## **5\. Spatial Semantic Grounding**

Đây là bước hợp nhất quan trọng nhất của Business Workflow.

Hệ thống tạo một **Property Spatial Knowledge Model** gồm:

* `Property`: mô tả và metadata cấp bất động sản.  
* `Room`: tên phòng, loại phòng, các thuộc tính và room connectivity.  
* `Checkpoint`: panorama ID, room ID, camera position/orientation, scene asset reference.  
* `Observation`: objects, visual highlights và những đặc điểm quan sát được.  
* `Navigation`: checkpoint adjacency, doors, walkable regions và transitions.  
* `Narration`: script, audio asset và camera keyframes.

Mỗi thuộc tính được gắn một nguồn thông tin và trạng thái:

| Evidence Type | Ý nghĩa |
| ----- | ----- |
| `verified` | Dữ liệu do Business cung cấp hoặc xác nhận |
| `observed` | Đặc điểm AI nhận diện từ panorama |
| `inferred` | Kết quả AI suy luận, chưa được xác minh |
| `unknown` | Chưa đủ thông tin để kết luận |

Ví dụ: `CP02 → Bedroom 1 → two beds → panoramic visual evidence → camera pose → 3D scene region`.

Thông tin như diện tích, vật liệu, hướng nhà hoặc giá bán không được tự suy diễn thành sự thật khi thiếu bằng chứng.

**Output:** Một structured knowledge layer để Business Tour Builder và Customer Spatial AI Chatbot cùng sử dụng.

## **6\. AI Guided Tour Generation**

Sau khi hoàn tất semantic mapping, LangGraph tạo guided tour dựa trên room graph, checkpoint locations và validated navigation paths.

**Tour Planning**

* Chọn thứ tự phòng và những điểm nổi bật cần giới thiệu.  
* Đề xuất camera path, viewing direction và thời gian dừng ở mỗi checkpoint.  
* Ưu tiên transitions hợp lệ, không xuyên tường hoặc đi vào vùng 3D thiếu dữ liệu.

**Narration Generation**

* GPT tạo lời thuyết minh riêng theo từng checkpoint, sử dụng verified metadata và visual observations.  
* Hỗ trợ lựa chọn ngôn ngữ, phong cách, độ dài và voice.  
* OpenAI TTS tạo narration audio theo từng đoạn.

**Tour Assembly**

* Ghép camera keyframes, lời thuyết minh, audio timing và hotspot actions.  
* Tạo timeline có thể chỉnh sửa trong Business Portal.  
* Cho phép tái sinh riêng narration/audio hoặc camera path mà không phải chạy lại PanSplat.

## **7\. Business Review — Human-in-the-Loop**

Workflow sử dụng LangGraph persistence và `interrupt()` để dừng tại bước phê duyệt.

Business Portal cung cấp một Tour Editor gồm ba vùng:

| Workspace | Chức năng |
| ----- | ----- |
| **3D Scene Viewer** | Preview reconstruction, checkpoint positions, hotspots và navigation |
| **Floorplan / Room Map** | Kiểm tra cấu trúc phòng, kết nối, sửa mapping và vị trí checkpoint |
| **Tour & Property Editor** | Sửa metadata, AI narration, voice, tour sequence và camera movement |

Business có thể chọn **Approve**, **Edit & Regenerate** hoặc **Request Reconstruction Fix**. LangGraph tiếp tục từ trạng thái đã lưu và chỉ chạy lại những bước liên quan đến thay đổi.

Mọi lần publish tạo một version riêng; bản chưa duyệt không được công khai.

## **8\. Export & Publishing**

### **A. Interactive 3D Web Tour**

Xuất một website hoặc embeddable viewer gồm:

* Gaussian Splatting scene được tối ưu cho web.  
* Free-roam trong các khu vực đã xác nhận có navigation geometry an toàn.  
* Checkpoint navigation và room switching.  
* AI Guided Tour với camera movement, voice narration và Play/Pause.  
* Clickable hotspots và contextual property information.  
* Spatial AI Chatbot có thể truy xuất dữ liệu checkpoint đã được Business phê duyệt.

**Fallback:** Khi reconstruction chưa đủ chất lượng, viewer chuyển sang hybrid 3D/checkpoint mode hoặc liên kết panorama 360°, thay vì cho phép di chuyển xuyên qua vùng không đáng tin cậy.

### **B. MP4 Video Export**

Tour timeline → Validated Camera Path → Gaussian Scene Rendering → Audio Synchronization → FFmpeg → MP4.

Sử dụng cùng tour configuration với web viewer, hỗ trợ video 16:9 và 9:16. Có thể xuất video marketing với narration và captions mà không cần chạy lại AI reconstruction.

## **9\. Technical Architecture**

| Layer | Proposed Stack |
| ----- | ----- |
| Business Orchestration | Python, LangGraph StateGraph, persistent checkpointer |
| AI Scene Understanding | GPT Multimodal / Vision |
| 3D Reconstruction | Pretrained PanSplat, GPU worker |
| Spatial Processing | Pose estimation, layout estimation, Blender \+ Blender MCP |
| Semantic Processing | GPT structured outputs, Pydantic validation |
| Narration & Voice | GPT, OpenAI TTS |
| Backend & Jobs | FastAPI, Redis-backed task queue, GPU/Blender workers |
| Storage | PostgreSQL, S3-compatible object storage |
| 3D Web Viewer | Next.js \+ PlayCanvas / Gaussian Splat Viewer |
| Video Export | Camera renderer \+ FFmpeg |

LangGraph State lưu job IDs, input references, checkpoints, asset references, confidence scores, review status và output versions. Các file ảnh và 3D lớn được lưu trong object storage, không lưu trực tiếp trong graph state.

Workflow phải hỗ trợ retry, idempotency, caching và partial regeneration để tránh chạy lại những GPU jobs tốn chi phí.

## **10\. MVP Implementation Priority**

| Priority | Deliverable |
| ----- | ----- |
| **P0** | Panorama upload, GPT scene analysis, metadata grounding, 3D reconstruction một khu vực và checkpoint mapping |
| **P0** | Tự sinh narration, TTS, guided tour configuration và Business Preview |
| **P0** | Publish interactive viewer với checkpoint navigation và contextual information |
| **P1** | Blender-generated draft floorplan, proxy geometry và free-roam trong vùng hợp lệ |
| **P1** | Business HITL editing, partial regeneration và MP4 export |
| **P2** | Robust multi-room reconstruction, automatic topology correction và advanced free-roam navigation |

**Recommended demo:** Dùng 4–6 panorama có overlap tốt, tập trung tái dựng 1–2 khu vực liên thông. Chứng minh quy trình tự động từ upload đến 3D scene, enriched checkpoints, narrated tour và interactive website. Nếu dữ liệu không đủ cho multi-room free-roam, sử dụng checkpoint transitions thay vì tạo chuyển động giả.

## **11\. Final Product Outcome**

Business chỉ cần upload panorama và description, bổ sung floorplan/metadata nếu có. Estagent tự động tạo một bản nháp tour 3D có ngữ nghĩa, thuyết minh và điều hướng; Business kiểm tra, sửa đổi rồi xuất bản.

**Core Differentiator:** Không chỉ tạo mô hình 3D đẹp, Estagent biến từng không gian được tái dựng thành một tài sản số có thể khám phá, hiểu ngữ cảnh, thuyết minh và tương tác thông minh.

