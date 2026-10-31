# **ESTAGENT — AI Tour Generation Studio**

**UI/UX Technical Specification**

## **1\. Design Objective**

Thiết kế một **AI-Native Generation Workspace**, cho phép Business trực tiếp quan sát và tương tác với quá trình LangGraph xây dựng Intelligent 3D Property Tour.

Giao diện lấy cảm hứng từ cách ChatGPT trình bày công việc AI theo thời gian thực, nhưng được tối ưu riêng cho 3D Real Estate.

**Core UX Principle:**

**Input Once → Watch AI Work → Explore Results → Refine → Publish.**

Thay vì hiển thị bảng kỹ thuật với nhiều node, logs và tham số, hệ thống sử dụng một **Vertical AI Activity Stream**. Mỗi công đoạn tạo ra một activity card gồm trạng thái, giải thích ngắn gọn và kết quả trực quan.

Người dùng có thể quan sát toàn bộ quy trình, mở rộng kết quả từng bước và chỉnh sửa những phần cần thiết.

---

## **2\. Main User Journey**

### **Stage A — Create Property Tour**

**Page:** `/business/create`

Trang đầu tiên sử dụng giao diện tối giản với một khu vực nhập liệu trung tâm.

**A. Panorama Upload**

* Drag & drop nhiều ảnh panorama 360°.  
* Hiển thị ảnh preview dưới dạng thumbnails, có thể click để xem 360°.  
* Tự động kiểm tra định dạng, chất lượng và ảnh trùng.  
* Cho phép đổi tên ảnh và gán room label nếu cần.

**B. Property Description**

Một text editor lớn cho phép Business mô tả bất động sản tự nhiên, giống như nhập prompt trong ChatGPT.

Ví dụ:

"Tạo một tour cho căn hộ 2 phòng ngủ, có phòng khách liên thông với bếp và một ban công. Phong cách giới thiệu hiện đại, chuyên nghiệp, giọng nữ tiếng Việt. Hãy ưu tiên giới thiệu không gian sinh hoạt chung và ánh sáng tự nhiên."

**C. Additional Property Data**

Một mục mở rộng chứa:

* Optional floorplan upload.  
* Property metadata.  
* Room labels, floor information.  
* Tour language, narration voice, presentation style.

AI tự trích xuất các thông tin có cấu trúc từ description để giảm thao tác nhập liệu. Business có thể sửa các thông tin AI đã phân loại.

**Primary CTA:** `Generate 3D Property Tour`

Sau khi nhấn Generate, hệ thống tạo `project_id`, `generation_id` và LangGraph execution thread, sau đó điều hướng sang Generation Studio.

---

## **3\. AI Generation Workspace Layout**

**Page:** `/business/projects/:id/generate`

Giao diện desktop gồm ba khu vực chính:

| Region | UI Component | Responsibility |
| ----- | ----- | ----- |
| **Left Sidebar — 20%** | Project Navigator | Property information, uploaded assets, project settings, generation history |
| **Center — 48%** | AI Activity Stream | Hiển thị các bước LangGraph theo thời gian thực, nội dung AI, image previews và trạng thái |
| **Right — 32%** | Live Visual Preview | Xem panorama, floorplan, 3D model và các kết quả đang được tạo |

Tỷ lệ là định hướng responsive, không phải kích thước cố định.

**Top Navigation**

* Property name và generation status.  
* Saved / Running / Needs Review / Completed.  
* Preview Tour.  
* Review & Publish (chỉ khả dụng khi đáp ứng điều kiện).

**Center Activity Stream**

Luồng nội dung phát triển theo chiều dọc. Mỗi node hoặc nhóm tác vụ có một activity card mới xuất hiện khi backend bắt đầu xử lý.

Các activity card hoàn thành được giữ lại, cho phép Business cuộn lên và kiểm tra kết quả cũ.

**Right Preview Panel**

Tự thay đổi nội dung dựa trên activity hiện tại hoặc kết quả người dùng đang chọn.

Có bốn preview modes:

`Panorama` \| `Floorplan` \| `3D House` \| `Tour Preview`

Khi một asset chưa sẵn sàng, hiển thị placeholder thay vì preview giả.

---

## **4\. Real-Time LangGraph Activity Stream**

### **Step 01 — Input Understanding**

**UI Title:** `Analyzing your property`

Hiển thị:

* Các thumbnail panorama đã upload.  
* Số lượng ảnh hợp lệ và những ảnh cần chỉnh sửa.  
* Property metadata được AI trích xuất.  
* Tóm tắt yêu cầu về phong cách tour và narrator.

**Example Activity Message:**

"Your property information has been organized. All six panoramas are ready for scene analysis."

**Visual Output:** Input gallery và structured property summary.

### **Step 02 — Scene Understanding**

**UI Title:** `Understanding your spaces`

GPT Vision phân tích panorama và cập nhật các phát hiện khi hoàn thành từng checkpoint.

Ví dụ các kết quả có thể xuất hiện:

* Living Room — CP01.  
* Kitchen — CP02.  
* Bedroom — CP03.  
* Balcony — CP04.

Mỗi ảnh có room label, objects được nhận diện và một bản tóm tắt ngắn.

**Visual Output:** Image gallery, room cards và các visual annotations có tọa độ đáng tin cậy.

### **Step 03 — Spatial Layout Generation**

**UI Title:** `Mapping your property layout`

Hệ thống phân tích floorplan hoặc ước lượng cấu trúc không gian.

**Visual Output:**

* Interactive 2D floorplan.  
* Room boundaries và room labels.  
* Sơ đồ kết nối các phòng.  
* Checkpoint positions được đề xuất.  
* Những khu vực cần xác minh.

Nếu không có floorplan, UI phải nêu rõ sơ đồ là kết quả ước lượng.

Khi spatial layout không đủ chắc chắn, xuất hiện một inline review card:

`Review Layout` \| `Edit Rooms` \| `Confirm & Continue`

Không chuyển sang dựng mô hình 3D chính thức nếu các vấn đề quan trọng về topology chưa được giải quyết.

### **Step 04 — Blender 3D House Generation**

**UI Title:** `Building your 3D house`

LangGraph kích hoạt Blender MCP worker và cập nhật các mốc có thể quan sát được:

1. Creating floor and wall geometry.  
2. Building room structures.  
3. Applying materials and room labels.  
4. Registering checkpoint anchors.  
5. Rendering preview and exporting 3D model.

**Visual Output:**

* Blender render thumbnails.  
* 3D house overview khi có preview asset.  
* 3D Model Viewer thực tế sau khi GLB được xuất thành công.

**Interaction:** Khi mô hình sẵn sàng, Business có thể orbit, zoom, chọn phòng và mở rộng viewer.

Không cần stream trực tiếp viewport Blender. Hệ thống có thể gửi các preview renders ở những mốc quan trọng.

### **Step 05 — Checkpoint Mapping**

**UI Title:** `Connecting rooms to panoramic views`

Hệ thống liên kết các panorama vào room meshes và checkpoint anchors trong mô hình 3D.

**Visual Output:** Split Preview:

* Bên trái: 3D dollhouse có checkpoint markers.  
* Bên phải: Panorama gốc tương ứng.

Chọn một checkpoint trong 3D sẽ highlight ảnh panorama tương ứng, và ngược lại.

Cho phép chỉnh room mapping, vị trí checkpoint và orientation khi cần.

### **Step 06 — Semantic Enrichment**

**UI Title:** `Enriching your property information`

LangGraph hợp nhất ảnh, room context, description và metadata.

**Visual Output:**

* Room descriptions.  
* AI-detected highlights.  
* Property features.  
* Verified / Observed / Inferred information.  
* Contextual content gắn với từng checkpoint.

Business có thể chỉnh sửa hoặc xác nhận dữ liệu trước khi đưa vào narration.

### **Step 07 — Navigation Generation**

**UI Title:** `Creating your interactive tour`

Hệ thống tạo:

* Arrow hotspots giữa các panorama checkpoints.  
* Room-to-room connections.  
* 3D-to-Panorama transitions.  
* Tour sequence.

**Visual Output:** Panorama preview với navigation arrows và checkpoint map.

Business có thể thử bấm mũi tên để kiểm tra các đường dẫn.

### **Step 08 — AI Narration Generation**

**UI Title:** `Preparing your AI-guided tour`

LangGraph tạo narration scripts dựa trên enriched checkpoint data.

**Visual Output:**

* Property introduction.  
* Narration text cho từng phòng.  
* Voice generation status.  
* Audio player khi TTS hoàn thành.  
* Suggested highlights và tour timeline.

**Available Actions:**  
`Play Audio` \| `Edit Script` \| `Regenerate Voice`

Narration được tạo theo từng segment để cho phép chỉnh sửa riêng lẻ.

### **Step 09 — Final Tour Assembly & Validation**

**UI Title:** `Preparing your final experience`

Hệ thống kiểm tra:

* Mô hình 3D và room/checkpoint mapping.  
* Panorama navigation.  
* Narration timing.  
* Metadata consistency.  
* Hai chế độ xem và chuyển đổi qua lại.

**Visual Output:** Interactive Dual-View Preview và QA Summary.

Issues được hiển thị dưới dạng actionable cards với vị trí cụ thể và hướng xử lý.

### **Step 10 — Ready for Review**

**UI Title:** `Your property tour is ready`

Hiển thị completion summary với:

* 3D House Preview.  
* Panorama Tour Preview.  
* Property Information.  
* Narration & Guided Tour.  
* Những thông tin còn cần Business xác nhận.

**Primary Actions:**

`Open Tour Editor` \| `Approve & Publish` \| `Export Video`

---

## **5\. Activity Card Design System**

Mỗi LangGraph activity được hiển thị bằng một card có cấu trúc thống nhất.

**Card Anatomy**

* Step icon hoặc trạng thái.  
* Title mô tả công việc bằng ngôn ngữ tự nhiên.  
* Live status message.  
* Result summary.  
* Inline visual artifact.  
* Optional action controls.  
* Expandable details.

**Execution States**

| Status | UI Treatment |
| ----- | ----- |
| `queued` | Text trung tính, chưa có animation |
| `running` | Subtle activity animation hoặc spinner |
| `completed` | Checkmark, result artifact được hiển thị |
| `needs_review` | Inline review controls, chờ Business |
| `failed` | Error explanation, Retry hoặc Edit Input |
| `skipped` | Giải thích vì sao bước này không cần chạy |

Trạng thái được cập nhật bằng backend events, không dự đoán từ thời gian hoặc animation.

**Animation Behavior**

* Card mới xuất hiện bằng fade/slide nhẹ.  
* Timeline connector mở rộng khi bắt đầu bước mới.  
* Image preview hiện ra khi asset sẵn sàng.  
* Card hoàn thành thu gọn phần kỹ thuật nhưng giữ summary và visual output.  
* Nếu người dùng đang đọc một bước cũ, không tự động cuộn xuống làm gián đoạn. Hiển thị "New updates" để quay lại bước đang chạy.

Người dùng được phép expand/collapse từng step, xem lịch sử và mở preview fullscreen.

---

## **6\. Inline Visualizations**

Giao diện nên hỗ trợ các loại artifact riêng, thay vì dùng một card thông thường cho mọi dữ liệu.

| Artifact | Renderer |
| ----- | ----- |
| Panorama Image Gallery | Thumbnail Grid \+ Lightbox |
| AI Scene Recognition | Image Viewer \+ Annotations |
| Floorplan | Interactive SVG/Canvas |
| Room Connectivity | Spatial Graph Visualization |
| 3D House Model | Three.js / React Three Fiber |
| Checkpoint Mapping | Linked 3D \+ Panorama Viewer |
| Property Metadata | Editable Structured Data |
| Narration | Script Card \+ Audio Player |
| Tour Timeline | Sequence / Timeline Component |
| Final Experience | Dual-View Interactive Preview |

Mỗi artifact được lưu dưới một reference có thể truy xuất và mở lại, không chỉ là nội dung tạm thời trong activity stream.

---

## **7\. Interactive AI Assistant**

Ở cuối hoặc bên cạnh AI Activity Stream, cung cấp một ô nhập:

**"Ask Estagent to refine your tour..."**

Business có thể đưa ra chỉ dẫn như:

* "Đổi tên khu vực này thành Living Area."  
* "Hãy giới thiệu phòng khách ngắn gọn hơn."  
* "Chuyển phòng ngủ thành checkpoint cuối cùng."  
* "Sửa vị trí checkpoint số 3."  
* "Đổi narration sang giọng nam tiếng Anh."

AI xử lý yêu cầu thành những thao tác có cấu trúc và xác định các bước cần chạy lại.

**Important:** Chat interaction không được tự động sửa geometry hoặc metadata đã xác minh mà không có sự xác nhận phù hợp.

Lưu lịch sử chỉnh sửa để Business có thể theo dõi những thay đổi do AI thực hiện.

---

## **8\. LangGraph → Frontend Integration**

### **Backend Architecture**

LangGraph phát execution events; FastAPI đưa các events này đến frontend bằng SSE hoặc WebSocket.

**Event Flow:**

`LangGraph Nodes / Blender Worker → Event Aggregator → FastAPI Stream → React Activity Timeline → Artifact Preview`

Dữ liệu có hai luồng:

**A. Workflow State Events**

* Node started.  
* Node completed.  
* Node failed.  
* Interrupt / Review required.  
* Workflow resumed.  
* Generation completed.

**B. Artifact Events**

* Panorama analysis ready.  
* Floorplan preview ready.  
* Blender render ready.  
* 3D GLB ready.  
* Checkpoint mapping ready.  
* Narration audio ready.  
* Final tour ready.

### **Suggested Event Contract**

Mỗi UI event nên chứa:

| Field | Purpose |
| ----- | ----- |
| `event_id` | ID để deduplicate và replay |
| `generation_id` | Generation run hiện tại |
| `node_id` | LangGraph processing node |
| `event_type` | Status, message, artifact, error hoặc review request |
| `status` | Runtime state |
| `message` | Nội dung hiển thị cho Business |
| `artifact_type` | Image, floorplan, GLB, audio, data, tour |
| `artifact_url` | Tham chiếu asset đã tạo |
| `timestamp` | Thời điểm backend phát event |

LLM text có thể streaming theo token. Tuy nhiên, geometry, ảnh và audio nên xuất hiện khi worker thực sự tạo xong asset hợp lệ.

Nếu có progress percentage, chỉ dùng số liệu đo được từ worker. Với tác vụ không thể xác định tiến độ chính xác, dùng activity messages và milestone states.

### **Persistence & Recovery**

* Mỗi project có generation history.  
* LangGraph lưu state theo execution thread.  
* Frontend có thể reload và khôi phục activity history.  
* Các asset đã hoàn thành không bị mất khi kết nối bị gián đoạn.  
* Human approval sử dụng LangGraph interrupt/resume.  
* Chỉ những bước liên quan đến thay đổi được tái sinh.

Internal chain-of-thought, private prompts và raw debug traces không được hiển thị cho Business. Activity Stream chỉ hiển thị những thông tin công việc có thể kiểm chứng và phù hợp với người dùng cuối.

---

## **9\. Visual Design Direction**

**Theme:** Premium White SaaS, minimal, architectural, professional.

**Color System**

* Background: Warm white `#FAFBFA`.  
* Primary text: Charcoal `#172126`.  
* Secondary text: Slate gray.  
* Accent: Teal `#0D9488`.  
* Borders: Very light gray.  
* Cards: White surface, subtle shadows.

**Typography:** Geist hoặc Inter, phân cấp rõ, heading ngắn.

**Component Styling**

* Rounded cards 12–16px.  
* Soft shadows, không sử dụng gradient phức tạp.  
* Activity cards có khoảng trắng rộng và visual previews lớn.  
* Sidebar tối giản, icon line style.  
* Animation mượt, 200–350ms cho những chuyển đổi UI thông thường.  
* Responsive layout, mobile chuyển sang một cột và preview dạng expandable panel.

Hạn chế dùng quá nhiều màu trạng thái, icon, loading spinner hoặc văn bản dài.

**Design Goal:** Giao diện mang cảm giác một professional creative tool đang làm việc cùng người dùng, không giống màn hình theo dõi logs kỹ thuật.

---

## **10\. Generation Completion & Editor Handoff**

Sau khi workflow hoàn thành, giao diện không chuyển trang đột ngột.

Thay vào đó:

1. Activity Stream hiển thị final completion card.  
2. Right Preview mở Dual-View Tour.  
3. Business có thể xem toàn bộ kết quả.  
4. Chọn `Open Tour Editor` để chỉnh sửa chuyên sâu.  
5. Sau phê duyệt, chọn `Publish Interactive Tour` hoặc `Export MP4`.

Generation Studio là nơi tạo và theo dõi công việc AI. Tour Editor là nơi kiểm tra, hoàn thiện và xuất bản sản phẩm.

## **11\. MVP Scope**

**P0 — Essential Experience**

* Upload form \+ property description.  
* Vertical AI Activity Stream.  
* Real-time backend status events.  
* Panorama thumbnails và AI scene result cards.  
* Floorplan preview.  
* Blender model preview.  
* Checkpoint mapping preview.  
* Narration text/audio cards.  
* Final dual-view preview.  
* Business review & approval.

**P1 — Enhanced Workspace**

* Interactive AI refinement chat.  
* Inline editing.  
* Partial regeneration.  
* Expandable node details.  
* Generation version history.  
* Advanced progress visualization.

**P2 — Advanced Collaboration**

* Multi-user Business Review.  
* Collaborative annotations.  
* Tour comparison between versions.  
* Detailed AI execution analytics.

## **12\. Final UX Positioning**

**Estagent AI Tour Generation Studio** biến một LangGraph workflow phức tạp thành trải nghiệm AI trực quan, dễ hiểu và có khả năng tương tác theo thời gian thực.

Business không phải hiểu LangGraph, Blender MCP hay room-layout estimation.

Người dùng chỉ cần cung cấp dữ liệu, quan sát hệ thống xây dựng tour từng bước, xác nhận thông tin khi cần và xuất bản sản phẩm.

**Experience Statement:**

*Upload your property. Watch AI bring every space to life. Review, refine, and publish an intelligent 3D tour.*

