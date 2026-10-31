# **ESTAGENT – Business AI Tour Builder**

**LangGraph \+ Blender MCP \| Dual-View 3D Property Experience**

## **1\. Objective**

Estagent cho phép doanh nghiệp bất động sản upload ảnh panorama 360°, mô tả bất động sản và metadata tùy chọn để tự động xây dựng một **Intelligent Property Tour** gồm hai chế độ xem đồng bộ:

**A. Interactive 3D House View**

* Mô hình tổng quan ngôi nhà dạng 3D Dollhouse.  
* Xoay, zoom, chọn tầng, chọn phòng.  
* Click vào room hoặc checkpoint để phóng camera đến khu vực tương ứng.  
* Chuyển cảnh transition đẹp, thực tế vào panorama 360° để khám phá nội thất thực tế.

**B. Interactive 360° Panorama Tour**

* Xem ảnh panorama gốc với góc nhìn 360°.  
* Điều hướng giữa các checkpoint bằng mũi tên/hotspots.  
* Xem room information, enriched metadata và AI highlights.  
* Phát AI Guided Tour với narration tự động.

Hai view sử dụng chung một **Spatial Property Graph** và Tour Configuration, bảo đảm sự đồng nhất giữa mô hình nhà, checkpoint, dữ liệu không gian và nội dung AI.

### **Core Workflow**

Input → AI Understanding → Layout & Spatial Graph → Blender 3D Modeling → Checkpoint Registration → Semantic Grounding → AI Narration → Tour Assembly → Business Review → Dual-View Publishing.

**Design principle:** Blender tạo mô hình không gian 3D; Panorama Viewer trình bày nội thất thật. Không sử dụng Gaussian Splatting hoặc PanSplat.

---

## **2\. Input Specification**

| Input | Requirement |
| ----- | ----- |
| Panorama 360° | Required. Ảnh equirectangular của các vị trí trong bất động sản |
| Property Description | Required. Mô tả ngôi nhà, thông tin tổng quan |
| Property Metadata | Optional. Giá bán, diện tích, tiện nghi, thông số |
| Floorplan | Optional. Sơ đồ 2D hoặc bản vẽ kiến trúc |
| Room Labels / Order | Optional. Tên phòng, thứ tự chụp, liên kết giữa các ảnh |
| Camera Information | Optional. Hướng camera, vị trí hoặc chiều cao chụp |

### **Input Preprocessing**

* Kiểm tra ảnh, định dạng, độ phân giải và metadata.  
* Chuẩn hóa panorama và tạo perspective/cubemap views để GPT Vision phân tích.  
* Trích xuất structured property information từ description.  
* Tạo một `checkpoint_id` cố định cho mỗi panorama.  
* Nhận diện ảnh trùng, ảnh lỗi hoặc các vị trí không rõ phòng.

**Output:** Normalized Property Data \+ Panorama Asset Registry.

---

## **3\. LangGraph Processing Architecture**

Một LangGraph `StateGraph` điều phối toàn bộ workflow. Các tác vụ độc lập có thể thực thi song song, nhưng toàn bộ hệ thống dùng chung persistent workflow state.

| Node | Responsibility | Output |
| ----- | ----- | ----- |
| **N1. Input Processor** | Validate panorama, parse description và chuẩn hóa metadata | Property Input |
| **N2. Scene Understanding** | GPT Vision phân tích từng panorama, nhận diện phòng, nội thất, cửa, điểm nổi bật | Scene Semantic Records |
| **N3. Layout Estimation** | Phân tích floorplan hoặc dự đoán room layout từ panorama | Per-Room Layouts |
| **N4. Spatial Graph Builder** | Kết nối các phòng, xác định checkpoint positions, room topology và global coordinates | Spatial Property Graph |
| **N5. Blender 3D Builder** | Dùng Blender MCP tạo mô hình nhà chi tiết nội thất, đẹp, floor/walls, openings, checkpoint anchors | 3D House Model |
| **N6. Checkpoint Registration** | Mapping các ảnh panorama vào phòng và vị trí tương ứng trong mô hình 3D | Registered Checkpoints |
| **N7. Semantic Grounding** | Matching description, room data, observations và enrichment | Enriched Spatial Knowledge |
| **N8. Tour Navigation Builder** | Sinh arrows, panorama links, hotspot positions và 3D-to-360 transitions | Navigation Graph |
| **N9. AI Narration Builder** | Sinh nội dung thuyết minh, tour sequence, TTS và timing | Narrated Tour |
| **N10. Tour Package Builder** | Hợp nhất 3D assets, panorama assets, metadata, navigation và narration | Unified Tour Package |
| **N11. Quality Validator** | Kiểm định geometry, mapping, nội dung và trải nghiệm hai view | QA Report |
| **N12. Business HITL & Publisher** | Business review, chỉnh sửa và publish phiên bản đã duyệt | Published Property Tour |

N2 và N3 chạy song song. Các bước dựng 3D, sinh âm thanh và xử lý asset được giao cho dedicated workers.

## **4\. Spatial Reconstruction – Panorama to Blender 3D**

### **4.1. Room Layout Understanding**

Hệ thống sử dụng panorama và floorplan để suy luận cấu trúc không gian.

**Case A — Floorplan Available**

1. Phân tích floorplan để xác định room boundaries, walls, doors, floors và kích thước được cung cấp.  
2. GPT Vision nhận diện room type trong từng panorama.  
3. Matching panorama với các phòng trên floorplan dựa trên đặc điểm và metadata.  
4. Ước lượng camera/checkpoint positions và orientation trong global coordinate system.  
5. Business xác nhận các mapping không chắc chắn.

**Case B — No Floorplan**

1. Dùng room-layout estimation (ví dụ HorizonNet/DuLa-Net hoặc model tương đương) để suy luận cấu trúc phòng từ panorama.  
2. GPT Vision nhận diện các dấu hiệu liên kết không gian: cửa, hành lang, cầu thang và khu vực nối nhau.  
3. Ước lượng room adjacency và các vị trí panorama tương đối.  
4. Tổng hợp các room layouts thành draft floorplan/topology.  
5. Khi thiếu kích thước thực, sử dụng kích thước tương đối, đánh dấu `estimated`.  
6. Đưa draft floorplan cho Business kiểm tra và chỉnh sửa trước khi dựng 3D.

**Constraint:** Không thể bảo đảm phục dựng chính xác cả căn nhà, kích thước và các kết nối giữa phòng chỉ từ một số panorama độc lập. Nếu thiếu dữ liệu, Estagent tạo *approximate 3D spatial model*, thay vì khẳng định đó là bản sao đo đạc chính xác.

### **4.2. Spatial Property Graph**

LangGraph tạo cấu trúc trung gian gồm:

* `Property`: thông tin toàn bộ bất động sản.  
* `Floor`: tầng, cao độ, các phòng thuộc tầng.  
* `Room`: room ID, geometry, tên phòng và các đặc điểm không gian.  
* `Checkpoint`: panorama ID, room ID, vị trí và orientation.  
* `Connection`: liên kết giữa phòng và giữa checkpoints.  
* `Feature`: các tiện ích và đối tượng được AI xác định.  
* `Evidence`: nguồn và trạng thái xác minh thông tin.

Spatial Graph sử dụng một hệ tọa độ quy chiếu chung. Checkpoint có camera position và orientation tương ứng trên mô hình Blender.

**Output:** `spatial_graph.json` \+ `floorplan_draft.json`.

### **4.3. Blender MCP — Automated 3D House Builder**

LangGraph chuyển Spatial Graph thành một structured modeling plan, sau đó gọi Blender thông qua MCP worker để dựng mô hình 3D.

**Blender responsibilities:**

1. Tạo floors, walls và room boundaries theo spatial layout.  
2. Tạo door/window openings ở các vị trí đã xác định hoặc được Business chấp thuận.  
3. Dựng không gian nhiều tầng nếu layout hỗ trợ.  
4. Thêm vật liệu, ánh sáng và optional proxy furniture theo phong cách 3D Dollhouse.  
5. Gắn room IDs lên các nhóm mesh và đặt checkpoint anchors tương ứng.  
6. Thiết lập các camera views: isometric, top-down, room-focus.  
7. Render preview images để kiểm tra mô hình.  
8. Xuất mô hình thành `.blend` và `.glb` cho website.

Blender MCP được sử dụng như interface điều khiển Blender, chủ yếu thông qua Blender Python API.

**Modeling strategy:** Ưu tiên geometry có cấu trúc và procedural modeling dựa trên room graph, không yêu cầu LLM tạo toàn bộ mesh bằng các mô tả tự do.

Nội thất 3D mang tính minh họa khi không có đủ dữ liệu hình học. Hình ảnh panorama vẫn là nguồn thể hiện nội thất thực tế.

**3D output:**

* Editable Blender scene.  
* Optimized GLB asset.  
* Room-to-mesh ID mapping.  
* Checkpoint anchor coordinates.  
* Preview thumbnails và QA images.

---

## **5\. Checkpoint Registration & Dual-View Mapping**

Mỗi panorama là một checkpoint, được gắn với một room và một vị trí trong mô hình nhà 3D.

### **5.1. Registration Process**

1. Gán panorama vào `room_id`.  
2. Xác định vị trí checkpoint trong room coordinate system.  
3. Chuyển vị trí sang global coordinate system của 3D model.  
4. Căn chỉnh orientation của panorama với hướng camera trong không gian.  
5. Tạo checkpoint marker có thể click trong 3D.  
6. Xác định các checkpoint liên kết và hướng mũi tên trong ảnh panorama.

Nếu vị trí hoặc hướng nhìn chưa rõ, hệ thống lưu confidence và yêu cầu Business chỉnh sửa.

### **5.2. 3D → Panorama Transition**

Khi người dùng chọn một checkpoint trong 3D House View:

1. Frontend nhận `checkpoint_id`.  
2. Three.js lấy target anchor position và camera framing.  
3. Camera được animate tiến gần đến room/checkpoint.  
4. Giao diện chuyển từ 3D model sang 360° panorama bằng zoom/crossfade.  
5. Panorama Viewer mở đúng ảnh và orientation đã cấu hình.  
6. Room metadata, hotspots và narration tương ứng được kích hoạt.

Đây là **visual transition giữa hai rendering modes**, không phải chuyển động 3D chân thực liên tục xuyên qua hình học chưa được tái dựng.

### **5.3. Panorama → Panorama Navigation**

Trong Panorama Tour, mỗi checkpoint có một danh sách connected checkpoints.

Mỗi navigation hotspot chứa:

* Source checkpoint ID.  
* Target checkpoint ID.  
* Position trong ảnh panorama (`yaw`, `pitch`).  
* Hướng nhìn khi mở target checkpoint.  
* Navigation label và optional transition animation.

Khi bấm mũi tên, frontend chuyển từ panorama A sang panorama B và cập nhật active checkpoint.

### **5.4. Panorama → 3D Transition**

Khi người dùng chọn `3D View`:

1. Lấy current checkpoint và room ID.  
2. Xác định vị trí checkpoint tương ứng trong mô hình 3D.  
3. Chuyển sang 3D viewer và focus camera vào phòng đó.  
4. Highlight room/checkpoint hiện tại.  
5. Cho phép tiếp tục orbit, zoom và khám phá tầng khác.

**Result:** Hai viewer luôn đồng bộ active room, checkpoint và spatial context.

---

## **6\. AI Scene Understanding & Semantic Grounding**

### **6.1. Per-Panorama Understanding**

GPT Vision phân tích mỗi checkpoint để trích xuất:

* Room type và mục đích sử dụng.  
* Nội thất và thiết bị quan sát được.  
* Door/window locations và visual connections.  
* Architectural features, lighting và room highlights.  
* Các chi tiết có giá trị trong thuyết minh bất động sản.

Dữ liệu trả về dưới structured JSON và được validate bằng schema.

### **6.2. Metadata Matching & Enrichment**

LangGraph kết hợp:

`Panorama Observations + Property Description + Optional Metadata + Spatial Graph`

để tạo **Enriched Checkpoint Knowledge**.

Ví dụ:

`CP03 → Bedroom 1 → Floor 2 → Two Beds → Large Window → Connected Hallway → Narration Context`

Mỗi thông tin phải có provenance:

| Status | Meaning |
| ----- | ----- |
| `verified` | Business cung cấp/xác minh |
| `observed` | AI nhìn thấy từ panorama |
| `inferred` | AI suy luận, cần kiểm tra |
| `unknown` | Thiếu bằng chứng |

AI có thể tạo room summaries, key selling points, suggested descriptions và presentation highlights, nhưng không tự tạo dữ kiện về diện tích, vật liệu, giá trị hoặc số lượng phòng nếu không có căn cứ.

**Output:** Property Knowledge Base và Context Records sử dụng chung cho Business và Customer AI Assistant.

---

## **7\. Automated Panorama Tour & Navigation Generation**

Node Navigation Builder tạo tour dựa trên spatial graph đã xác minh.

### **Panorama Navigation**

* Tạo các arrow hotspots tại vị trí cửa, hành lang hoặc hướng dẫn đến checkpoint kế tiếp.  
* Tự thiết lập scene-to-scene links.  
* Gợi ý entry checkpoint, exit checkpoint và tour sequence.  
* Xác minh các liên kết hai chiều và tránh tạo những đường đi không có thật.

### **3D House Navigation**

* Tạo room selection targets từ các named 3D meshes.  
* Đặt checkpoint markers trong từng phòng.  
* Tạo camera focus preset cho mỗi room/checkpoint.  
* Sinh transition configuration để chuyển từ 3D sang panorama.

Vị trí và hướng arrows phải dựa trên checkpoint connections và orientation đã hiệu chỉnh, không chỉ dựa trên lời mô tả bằng ngôn ngữ tự nhiên.

**Output:** Unified Navigation Configuration.

---

## **8\. AI Narrated Tour Generation**

Giữ nguyên tính năng AI Narrator trong proposal ban đầu và mở rộng để hỗ trợ cả hai view.

### **8.1. Tour Planning**

LangGraph xây dựng tour itinerary dựa trên:

* Thứ tự các phòng và checkpoint.  
* Những điểm nổi bật nên giới thiệu.  
* Property description và verified metadata.  
* Các kết nối hợp lệ giữa checkpoints.  
* Ngôn ngữ, giọng đọc và thời lượng mong muốn.

### **8.2. Narration Generation**

GPT sinh hai cấp nội dung:

**Property-Level Narration**

* Giới thiệu tổng quan bất động sản.  
* Mô tả bố cục, số tầng và các đặc điểm được xác minh.  
* Có thể phát trong 3D Dollhouse View.

**Checkpoint-Level Narration**

* Nội dung riêng cho từng panorama.  
* Tập trung vào đặc điểm thực tế của phòng.  
* Có thể gắn với visual hotspots hoặc một hướng nhìn cụ thể.  
* Hỗ trợ khách hàng tạm dừng hoặc bỏ qua lời thuyết minh.

OpenAI TTS tạo audio theo từng narration segment để hệ thống có thể phát lại hoặc thay đổi từng phần mà không sinh lại toàn bộ tour.

### **8.3. Guided Tour Assembly**

Hệ thống tạo một timeline:

`Property Introduction → Checkpoint 01 → Checkpoint 02 → ... → Tour Summary`

Mỗi checkpoint có:

* Narration script và audio URL.  
* Initial yaw/pitch.  
* Optional camera rotation sequence.  
* Displayed highlights và metadata.  
* Duration, auto-next configuration.

Người dùng có thể tạm dừng guided tour, tự khám phá hoặc hỏi AI Assistant rồi tiếp tục.

---

## **9\. Unified Tour Package — Two View Outputs**

LangGraph không trực tiếp render hai giao diện trong trình duyệt. Thay vào đó, workflow xuất **một Unified Tour Package** chứa các dữ liệu và tài sản cần thiết để frontend tạo hai chế độ xem.

### **Shared Data Contract**

| Asset | Purpose |
| ----- | ----- |
| `house.glb` | Mô hình 3D toàn bộ bất động sản |
| `panoramas/` | Ảnh 360° và image tiles |
| `spatial_graph.json` | Floors, rooms, checkpoints, connections |
| `tour_manifest.json` | Cấu hình đồng bộ hai viewer |
| `semantic_data.json` | Enriched checkpoint knowledge |
| `navigation.json` | Hotspots, adjacency và 3D transitions |
| `narration/` | Scripts, audio và timing |
| `preview/` | Thumbnails, overview renders |

### **Output A — 3D Dollhouse View**

Frontend dùng Three.js/React Three Fiber để:

* Load mô hình `.glb`.  
* Orbit, zoom, pan và chọn tầng.  
* Click vào room meshes hoặc checkpoint markers.  
* Highlight room và hiển thị thông tin tương ứng.  
* Animate camera và chuyển vào panorama viewer.

### **Output B — 360° Panorama Tour**

Frontend dùng Marzipano hoặc Pannellum để:

* Hiển thị panorama 360°.  
* Xoay camera, zoom, chuyển scene bằng mũi tên.  
* Hiển thị hotspots, metadata và narration.  
* Chuyển về 3D Dollhouse View với active checkpoint được giữ nguyên.

Hai view chia sẻ một `selected_checkpoint_id`, `selected_room_id` và tour session state. Không phải tạo hai bản sao độc lập của dữ liệu.

### **Optional Output — MP4 Video**

Tour configuration được sử dụng để xuất video có:

* 3D house overview.  
* Room-focus transitions.  
* Panorama scene sequences.  
* Voice narration, captions và branding.

Video rendering do Blender/renderer worker và FFmpeg đảm nhiệm, không chạy bên trong LangGraph node theo kiểu xử lý từng frame.

---

## **10\. Business Review — Human-in-the-Loop**

LangGraph sử dụng persistence/checkpointing và `interrupt()` tại hai điểm phê duyệt.

**Stage A — Spatial Review (Conditional)**

Được kích hoạt khi floorplan hoặc room connectivity không chắc chắn.

Business có thể:

* Điều chỉnh floorplan và room boundaries.  
* Sửa room labels.  
* Xác nhận các cửa và liên kết giữa phòng.  
* Di chuyển checkpoint anchors và chỉnh orientation.

Sau khi xác nhận, workflow tiếp tục Blender 3D modeling.

**Stage B — Final Tour Review**

Business Portal có:

1. 3D Model Preview với room/checkpoint selection.  
2. Panorama Tour Preview với arrows và hotspots.  
3. Property & Narration Editor để duyệt metadata, scripts, audio và tour sequence.

Business chọn **Approve**, **Edit & Regenerate** hoặc **Reject**.

Để tiết kiệm tài nguyên, workflow chỉ tái tạo các asset bị ảnh hưởng:

| Change | Re-run |
| ----- | ----- |
| Sửa narration text | TTS \+ Tour Package |
| Sửa property metadata | Semantic validation \+ affected narration |
| Sửa hotspot | Navigation \+ Tour Package |
| Di chuyển checkpoint | Mapping \+ affected transitions |
| Sửa floorplan/room structure | Spatial Graph \+ Blender \+ affected mapping |
| Thay panorama | Scene Analysis \+ affected spatial/semantic processing |

Mỗi lần publish tạo một immutable version; bản nháp có thể tiếp tục chỉnh sửa độc lập.

---

## **11\. Technical Stack**

| Layer | Proposed Technology |
| ----- | ----- |
| AI Orchestration | Python, LangGraph StateGraph |
| Vision & Semantic AI | GPT multimodal, structured output |
| Room Layout Estimation | Panorama layout estimation model |
| Spatial Representation | JSON Spatial Graph \+ PostgreSQL |
| 3D Modeling | Blender, Blender MCP, Blender Python API |
| 3D Asset Export | glTF / GLB |
| 3D Web Viewer | Three.js \+ React Three Fiber |
| Panorama Viewer | Marzipano / Pannellum |
| AI Narration | GPT \+ OpenAI TTS |
| Backend | FastAPI \+ task workers |
| State & Queue | PostgreSQL Checkpointer \+ Redis Queue |
| Media Storage | S3-compatible object storage |
| Video Export | Blender renderer \+ FFmpeg |

Blender jobs phải được cô lập khỏi API server. LangGraph gọi các tool wrappers đã được kiểm soát, theo dõi job IDs và lưu references thay vì đưa file 3D lớn trực tiếp vào graph state.

## **12\. Quality Validation**

Workflow thực hiện các kiểm định trước khi publish:

**Spatial QA**

* Room mesh và floor geometry hợp lệ.  
* Checkpoint nằm trong phòng được gán.  
* Room labels và coordinates nhất quán.  
* Không có room connection không được xác nhận.

**Panorama QA**

* Mọi checkpoint đều có ảnh panorama.  
* Các navigation arrows trỏ đến checkpoint tồn tại.  
* Yaw/pitch của hotspot đã được xác định.  
* Không có liên kết sai hoặc vòng lặp bất thường.

**Semantic QA**

* Nội dung narration có nguồn xác thực.  
* Metadata không mâu thuẫn với dữ liệu được xác minh.  
* Các thuộc tính suy luận không được trình bày như dữ kiện chắc chắn.

**Publishing QA**

* GLB load được trên web.  
* Chuyển đổi 3D ↔ Panorama hoạt động đúng.  
* Narration và scene state đồng bộ.  
* 3D navigation, 360 tour và mobile controls hoạt động ổn định.

Các vấn đề nghiêm trọng phải được sửa hoặc Business chấp thuận cách xử lý trước khi publish.

---

## **13\. MVP Implementation Strategy**

### **P0 — Complete Dual-View Demo**

* Upload 6–8 panorama của một căn hộ hoặc căn nhà nhỏ.  
* GPT Vision phân tích và phân loại từng checkpoint.  
* Sử dụng floorplan có sẵn để tạo spatial graph đáng tin cậy.  
* Blender MCP tự động dựng simplified 3D Dollhouse và xuất GLB.  
* Mapping panorama checkpoints lên 3D model.  
* Panorama Tour có navigation arrows giữa các checkpoint.  
* Cho phép click phòng trong 3D để chuyển sang panorama.  
* Sinh narrated tour, metadata và guided sequence.  
* Business review rồi publish website.

### **P1 — Automated Spatial Intelligence**

* Ước lượng floorplan khi không có bản vẽ.  
* Xử lý floorplan uncertainty bằng Human-in-the-Loop.  
* Hỗ trợ nhiều tầng và room connectivity phức tạp.  
* Blender procedural furniture và nâng cấp visual style.  
* Partial regeneration, versioning và video export.

### **P2 — Advanced Experience**

* Nâng cao khả năng tự động nhận diện layout đa phòng.  
* Cải thiện chuyển cảnh 3D-to-360.  
* Contextual AI Assistant tương tác trực tiếp với room/checkpoint.  
* Advanced geometry refinement và 3D visualization quality.

---

## **13\. MVP Implementation Strategy**

### **P0 — Complete Dual-View Demo**

* Upload 6–8 panorama của một căn hộ hoặc căn nhà nhỏ.  
* GPT Vision phân tích và phân loại từng checkpoint.  
* Sử dụng floorplan có sẵn để tạo spatial graph đáng tin cậy.  
* Blender MCP tự động dựng simplified 3D Dollhouse và xuất GLB.  
* Mapping panorama checkpoints lên 3D model.  
* Panorama Tour có navigation arrows giữa các checkpoint.  
* Cho phép click phòng trong 3D để chuyển sang panorama.  
* Sinh narrated tour, metadata và guided sequence.  
* Business review rồi publish website.

### **P1 — Automated Spatial Intelligence**

* Ước lượng floorplan khi không có bản vẽ.  
* Xử lý floorplan uncertainty bằng Human-in-the-Loop.  
* Hỗ trợ nhiều tầng và room connectivity phức tạp.  
* Blender procedural furniture và nâng cấp visual style.  
* Partial regeneration, versioning và video export.

### **P2 — Advanced Experience**

* Nâng cao khả năng tự động nhận diện layout đa phòng.  
* Cải thiện chuyển cảnh 3D-to-360.  
* Contextual AI Assistant tương tác trực tiếp với room/checkpoint.  
* Advanced geometry refinement và 3D visualization quality.

## **14\. Final Architecture Decision**

Estagent Business Workflow sử dụng **LangGraph để điều phối toàn bộ quá trình xây dựng một bất động sản số có thể khám phá qua hai chế độ xem**.

* **Blender MCP:** Xây dựng mô hình cấu trúc 3D của ngôi nhà.  
* **Panorama Viewer:** Hiển thị không gian nội thất thực tế tại từng checkpoint.  
* **Spatial Property Graph:** Liên kết 3D geometry, panorama positions, room connectivity và metadata.  
* **GPT \+ TTS:** Làm giàu dữ liệu và tự động xây dựng AI Narrated Tour.  
* **Business Review:** Kiểm soát độ chính xác trước khi xuất bản.  
* **Unified Tour Package:** Cung cấp dữ liệu cho cả 3D Dollhouse View và Panorama Tour.

**Product outcome:** Doanh nghiệp tải ảnh panorama và mô tả bất động sản, Estagent tạo một bản nháp nhà 3D có thể tương tác, liên kết các checkpoint 360°, tự sinh nội dung thuyết minh và cho phép xuất bản thành một trải nghiệm tham quan trực tuyến thống nhất.

**Core Value Proposition:** *From 360° panoramas to an intelligent, navigable 3D property experience — automatically built, enriched, and narrated by AI.*

