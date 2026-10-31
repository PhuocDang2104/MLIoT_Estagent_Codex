# **Estagent – Intelligent 3D Real Estate Experience**

**Tagline:** *Don't just view a property. Explore it, understand it, and ask it anything.*

## **1\. Product Overview**

**Estagent** là nền tảng chuyển đổi các ảnh panorama 360° của bất động sản thành không gian 3D tương tác bằng Gaussian Splatting, tích hợp AI Agent có khả năng hiểu ngữ cảnh không gian, tự động tạo tour thuyết minh và hỗ trợ người mua tìm hiểu bất động sản một cách trực quan.

Thay vì chỉ xem hình ảnh, video hoặc chuyển đổi giữa các panorama checkpoints cố định, người mua có thể **khám phá không gian 3D, tham gia AI Guided Tour và tương tác với AI Assistant hiểu được vị trí hiện tại trong ngôi nhà**.

Sản phẩm phục vụ hai nhóm người dùng:

* **B2B — Real Estate Businesses:** Tạo, quản lý, tự động thuyết minh, xuất bản và xuất video tour 3D từ ảnh panorama 360° cùng property descriptions.  
* **B2C — Homebuyers:** Khám phá bất động sản trong không gian 3D, tương tác với Spatial AI Chatbot và tiếp cận thông tin về căn nhà, tiện ích xung quanh và thị trường bất động sản.

## **2\. Core Features**

### **A. Business Portal — Create & Manage 3D Tours**

| Feature | Functionality |
| ----- | ----- |
| **Panorama-to-3D Reconstruction** | Upload nhiều ảnh panorama 360° cùng bất động sản, sử dụng pretrained PanSplat để tạo biểu diễn 3D Gaussian Splatting |
| **Automatic Checkpoint Mapping** | Mỗi panorama tương ứng một main checkpoint, liên kết với camera pose trong không gian 3D |
| **AI Scene Understanding** | AI phân tích từng panorama kết hợp property description/metadata để nhận diện phòng, nội thất và đặc điểm nổi bật |
| **AI Metadata Grounding & Enrichment** | Tự động ghép thông tin phòng với checkpoint phù hợp, bổ sung visual context và semantic descriptions |
| **AI Narrated Tour Generation** | Một LangGraph workflow tự động sinh narration scripts, gọi OpenAI TTS và hoàn thiện guided tour |
| **Tour Editor & Publishing** | Business review, chỉnh sửa nội dung, checkpoint sequence, camera movement và xuất bản tour |
| **Video Export** | Render guided tour với camera transitions và voice narration thành video MP4 |

**Business Workflow:**

`360° Panoramas + Property Description/Metadata → PanSplat Reconstruction → LangGraph AI Tour Builder → Business Review → Publish / Export`

### **B. Buyer Experience — Explore with Spatial AI**

**1\. Immersive 3D Exploration**

* Khám phá ngôi nhà dưới góc nhìn first-person trong 3D Gaussian environment.  
* Click-to-move đến các vị trí hợp lệ trong vùng không gian được tái dựng, không chỉ giới hạn tại panorama checkpoints.  
* Xoay camera 360°, chuyển giữa các khu vực và xác định vị trí hiện tại.  
* Chuyển đổi giữa **Free Exploration** và **AI Guided Tour**.

**2\. Spatially Aware AI Chatbot — Core Differentiator**

AI Chatbot hiểu ngữ cảnh người dùng thông qua camera position, orientation, checkpoint/room context và property metadata.

| User Question | AI Capability |
| ----- | ----- |
| "Tôi đang đứng ở đâu?" | Xác định khu vực/checkpoint hiện tại và cung cấp thông tin tương ứng |
| "Khu vực này có gì đặc biệt?" | Kết hợp visual scene context và metadata để giải thích các đặc điểm nổi bật |
| "Phòng này có những tiện nghi gì?" | Truy xuất metadata và những đặc điểm đã nhận diện từ panorama |
| "Dẫn tôi đến phòng ngủ." | Xác định checkpoint đích và điều khiển camera đến khu vực phù hợp |
| "Cánh cửa trước mặt dẫn đến đâu?" | Dựa trên hướng nhìn, object grounding và room connectivity nếu đã được xác định |

**3\. AI-Powered Property Intelligence**

Chatbot có khả năng điều phối các external tools/APIs để đưa trải nghiệm vượt ra ngoài mô hình 3D.

* **Property Q\&A:** Trả lời về diện tích, nội thất, giá bán, công năng và các thuộc tính bất động sản từ property database.  
* **Location Intelligence:** Tìm trường học, bệnh viện, siêu thị, giao thông và tiện ích lân cận thông qua Maps API; hiển thị bản đồ, khoảng cách và thời gian di chuyển.  
* **Market Intelligence:** Truy xuất và phân tích dữ liệu giá bất động sản, trực quan hóa bằng charts/tables.  
* **Contextual Actions:** Chuyển checkpoint, điều khiển camera, highlight hotspots, hiển thị maps/charts hoặc phát guided tour theo yêu cầu.

**4\. AI Guided Tour**

Người mua có thể phát tour tự động với camera movement và narration tương ứng từng checkpoint, tạm dừng để khám phá hoặc đặt câu hỏi rồi tiếp tục hành trình.

## **3\. Unified LangGraph AI Architecture**

Estagent sử dụng **một hệ thống LangGraph orchestration thống nhất**, với hai execution paths theo vai trò người dùng:

* **Business Mode — AI Tour Builder:** Một workflow end-to-end xử lý toàn bộ scene understanding, metadata enrichment, narration và tour generation.  
* **Customer Mode — Spatial AI Chatbot:** Workflow tương tác nhiều lượt, tự phân loại intent, truy xuất context, gọi tools và tạo phản hồi.

LangGraph quản lý workflow state, nodes, routing và tool execution. OpenAI API do Codex Hackathon cung cấp được sử dụng để gọi GPT multimodal models và TTS models theo quyền truy cập thực tế, **không sử dụng Codex Harness**.

### **A. Business Mode — End-to-End AI Tour Builder**

**Objective:** Tự động biến ảnh panorama 360° và thông tin bất động sản thành một guided tour hoàn chỉnh, bao gồm nội dung, voice narration và camera transitions.

Business backend chỉ kích hoạt **một LangGraph workflow duy nhất** sau bước reconstruction/checkpoint initialization, thay vì tách thành nhiều agent workflows độc lập.

**LangGraph Execution Flow:**

`Panoramas + Property Description + Optional Metadata → Scene Understanding → Metadata Matching → Context Enrichment → Narration Generation → Content Validation → OpenAI TTS → Tour Sequencing & Assembly → Completed Tour`

**Processing Nodes:**

**1\. Scene Understanding**

* GPT Vision phân tích nội dung từng panorama.  
* Nhận diện room type, objects, layout và những đặc điểm quan sát được.  
* Mỗi panorama được liên kết với một checkpoint ID và camera pose.

**2\. Metadata Matching & Context Enrichment**

* Đọc property description và metadata nếu có.  
* So khớp thông tin phòng với visual features để xác định checkpoint tương ứng.  
* Tổng hợp scene observations và property attributes thành structured checkpoint context.  
* Đánh dấu những trường hợp không đủ bằng chứng hoặc có nhiều khả năng matching.

**Example:**

* `Panorama_02`: AI nhận diện hai giường, tủ quần áo và cửa sổ.  
* `Property Description`: "Bedroom 1 — Two beds, wardrobe, large window."  
* `Enriched Context`: `CP02 → Bedroom 1`, với room metadata, visual highlights và thông tin đã đối chiếu.

**3\. Narration Generation & Validation**

* GPT lựa chọn highlights cho từng checkpoint.  
* Tạo narration script tự nhiên, phù hợp phong cách real estate tour.  
* Kiểm tra nội dung dựa trên metadata và visual observations, tránh tự suy diễn thuộc tính chưa được xác minh.

**4\. Voice & Tour Assembly**

* Gọi OpenAI TTS để chuyển narration scripts thành audio.  
* Đề xuất thứ tự checkpoint và hướng camera tập trung vào các điểm nổi bật.  
* Tạo camera transitions, audio timing và timeline cho toàn bộ tour.  
* Lưu tour configuration, narration scripts và audio assets.

**5\. Business Review & Export**

Workflow trả về một tour draft hoàn chỉnh để Business xem lại, chỉnh sửa và phê duyệt. Sau khi được xác nhận, hệ thống cho phép publish interactive tour hoặc render video MP4.

**Output:** Checkpoint metadata, enriched scene context, narration scripts, audio files, tour timeline và camera keyframes.

### **B. Customer Mode — Spatial AI Chatbot**

**Objective:** Cung cấp một AI Assistant hiểu vị trí hiện tại của người mua, chủ động lựa chọn công cụ và thực hiện các hành động trong 3D experience.

Cùng hệ thống LangGraph được gọi với Customer Mode, sử dụng conversational state và tool-routing logic.

**LangGraph Execution Flow:**

`User Query + Spatial Context → Intent Detection → Context Retrieval / Tool Orchestration → Tool Execution (if needed) → GPT Response Generation → Structured UI Actions`

**Processing Nodes:**

**1\. Spatial Context Resolution**

* Nhận camera position, orientation và checkpoint/room context từ web viewer.  
* Truy xuất enriched checkpoint metadata đã được Business workflow tạo trước đó.

**2\. Intent Detection & Orchestration**

Phân loại và định tuyến yêu cầu của người dùng theo nhóm:

* Property Q\&A  
* Spatial Navigation  
* Scene Understanding  
* Nearby Amenities / Location Intelligence  
* Market Intelligence  
* General Conversation

**3\. Tool Execution**

Chatbot chủ động gọi các tools phù hợp, chẳng hạn:

* `get_property_info`  
* `get_current_scene_context`  
* `navigate_to_checkpoint`  
* `search_nearby_places`  
* `get_market_data`  
* `render_visualization`  
* `play_guided_tour`

Tool results được đưa trở lại LangGraph state để GPT tổng hợp và trả lời.

**4\. Response & UI Actions**

AI trả về câu trả lời ngôn ngữ tự nhiên cùng optional structured actions như `navigate_to_checkpoint`, `highlight_hotspot`, `show_map`, `render_chart` hoặc `play_tour`.

Backend/frontend xác thực và thực thi hành động; LangGraph duy trì hội thoại nhiều lượt thông qua conversation state.

## **4\. Suggested Technical Architecture**

Hệ thống gồm ba lớp: **3D Reconstruction**, **Unified LangGraph AI Orchestration** và **Interactive Experience**.

### **A. 3D Reconstruction Pipeline**

`360° Panoramas → Camera Pose Estimation / Registration → Pretrained PanSplat Inference → Gaussian Scene Alignment → 3D Viewer Assets`

* **Input:** Nhiều panorama 360° thuộc cùng một bất động sản, ưu tiên những góc chụp có overlap.  
* **Reconstruction:** PanSplat (CVPR 2025\) dùng pretrained weights để dự đoán spherical Gaussian representation từ các cặp panorama.  
* **Scene Integration:** Căn chỉnh camera poses và các reconstructed regions về hệ tọa độ chung.  
* **Checkpoint Initialization:** Mỗi panorama gốc tạo một main checkpoint gắn với camera pose tương ứng.  
* **Navigation:** Walkable geometry, collision constraints và camera movement rules giúp di chuyển trong các vùng hợp lệ.

PanSplat là pipeline xử lý 3D độc lập, không nằm trong LangGraph AI inference flow.

### **B. Unified LangGraph Orchestration**

Một LangGraph application sử dụng routing theo `execution_mode`:

`START → Mode Router → [Business Tour Builder / Customer Chatbot] → Output`

| Execution Mode | Trigger | Responsibilities |
| ----- | ----- | ----- |
| **Business – Tour Builder** | Business tạo hoặc tạo lại tour | Scene understanding, metadata matching, context enrichment, narration, TTS và tour assembly |
| **Customer – Chatbot** | Người mua gửi tin nhắn | Intent detection, spatial context retrieval, tool orchestration, response và UI actions |

**Shared Data Layer:** Hai execution paths dùng chung checkpoint records, property metadata, enriched scene context và tour assets. Business Mode xử lý và lưu tri thức không gian; Customer Mode tái sử dụng dữ liệu đó khi tương tác.

### **C. Real-Time Interactive Experience**

`Next.js 3D Viewer → FastAPI → LangGraph Chatbot → OpenAI API / External Tools → Response + UI Actions`

**Suggested Tech Stack:**

| Layer | Technologies |
| ----- | ----- |
| 3D Reconstruction | Pretrained PanSplat, Gaussian Splatting |
| Frontend & 3D Viewer | Next.js, Three.js / PlayCanvas, Gaussian Splat Viewer |
| Backend | Python FastAPI, GPU workers |
| AI Orchestration | **LangGraph (Python), unified StateGraph** |
| AI Models | **GPT multimodal / Vision \+ OpenAI TTS via Hackathon-provided OpenAI API** |
| Database & Storage | PostgreSQL, object storage, checkpoint/context database |
| External Intelligence | Google Maps/Places API, geocoding, routing, real-estate data APIs |
| Video Export | Camera path rendering, audio synchronization, FFmpeg |
| Visualization | 3D overlays, maps, charts, tables |

## **5\. MVP Scope — Hackathon Demo**

**Objective:** Chứng minh end-to-end workflow từ panorama 360° và property description đến interactive 3D property tour có AI-generated narration và context-aware chatbot.

| Priority | Deliverable |
| ----- | ----- |
| **P0** | Reconstruct một khu vực nhà từ panorama 360° bằng pretrained PanSplat và hiển thị trên web |
| **P0** | Tự khởi tạo checkpoint từ panorama và liên kết camera poses |
| **P0** | Một Business LangGraph workflow xử lý scene understanding → metadata enrichment → narration → OpenAI TTS → tour assembly |
| **P0** | Spatial AI Chatbot với intent routing, context retrieval và property Q\&A |
| **P0** | Chatbot gọi Maps API để tìm và trực quan hóa tiện ích xung quanh |
| **P1** | Guided Tour 3–5 checkpoints, audio narration, camera transitions và Play/Pause |
| **P1** | Checkpoint navigation và click-to-move trong vùng 3D hợp lệ |
| **P1** | Business review/editor, publishing và MP4 video export |
| **P2** | Market intelligence, advanced object grounding và multi-room free-roam nâng cao |

### **Suggested Demo Scenario**

1. **Business** upload 3–5 panorama của một bất động sản và property description.  
2. **PanSplat** reconstruct 3D scene từ các cặp panorama phù hợp, hệ thống khởi tạo checkpoint.  
3. **Business LangGraph Flow** phân tích panorama, tự mapping metadata và làm giàu ngữ cảnh từng checkpoint.  
4. Trong cùng workflow, GPT sinh narration scripts, OpenAI TTS tạo voice-over, hệ thống hoàn thiện tour configuration.  
5. **Business** review, chỉnh sửa, publish interactive tour hoặc xuất video MP4.  
6. **Buyer** mở 3D tour, khám phá phòng ngủ và hỏi: "Phòng này có gì nổi bật?" → AI trả lời dựa trên checkpoint context.  
7. **Buyer hỏi:** "Dẫn tôi đến phòng khách." → LangGraph gọi navigation tool và chuyển camera.  
8. **Buyer hỏi:** "Gần căn nhà có siêu thị nào?" → LangGraph gọi Maps API, hiển thị kết quả trên bản đồ.  
9. **Buyer** kích hoạt Guided Tour để xem toàn bộ hành trình kèm thuyết minh.

## **6\. Technical Considerations & Feasibility**

* **PanSplat Reconstruction:** PanSplat chủ yếu xử lý các cặp panorama có quan hệ camera xác định; reconstruction nhiều phòng cần bổ sung pose registration, scene integration và kiểm tra alignment.  
* **Free-Roam Navigation:** Gaussian Splatting không tự cung cấp collision geometry hay navigation mesh. Di chuyển chỉ được hỗ trợ trong vùng reconstruction đáng tin cậy.  
* **Checkpoint Grounding:** Mỗi panorama có checkpoint ID rõ ràng, nhưng việc gán room metadata có thể không chắc chắn; cần lưu confidence/validation status và cho phép Business xác nhận.  
* **LangGraph Architecture:** Một unified StateGraph với hai execution paths; Business Mode thực thi một workflow theo chuỗi, Customer Mode sử dụng conditional routing và tool-calling loops.  
* **AI Reliability:** Phân biệt thông tin được xác minh từ property metadata với đặc điểm quan sát từ panorama; không tự suy diễn diện tích, vật liệu, công năng hoặc cấu trúc chưa có căn cứ.  
* **Tour Generation:** LangGraph điều phối narration và TTS, trong khi camera animation và MP4 encoding được xử lý bởi các rendering services độc lập.  
* **API & Deployment:** Cần xác minh GPT/TTS model availability, API quotas, GPU requirements, Gaussian export compatibility, bản quyền dữ liệu và giấy phép model.

## **7\. Unique Value Proposition & Business Model**

Estagent kết hợp ba giá trị cốt lõi:

**Reconstruct — Panorama to Interactive 3D**

Chuyển các panorama 360° thành không gian 3D có chiều sâu, tạo trải nghiệm khám phá linh hoạt hơn panorama-based tours truyền thống.

**Understand — Automated Spatial Storytelling**

Tự động phân tích panorama, liên kết property metadata và tạo guided tour hoàn chỉnh với narration, voice-over và camera transitions thông qua một AI workflow xuyên suốt.

**Interact — Context-Aware AI Property Agent**

Cho phép người mua trò chuyện với AI hiểu ngữ cảnh không gian, truy xuất thông tin, điều hướng tour và kết nối các nguồn dữ liệu bên ngoài để hỗ trợ quyết định mua nhà.

**Business Model:** B2B SaaS cho các công ty bất động sản, môi giới và listing platforms; thu phí theo số tour, gói AI features, reconstruction resources và lưu trữ. Người mua truy cập qua link chia sẻ hoặc embedded tour.

**Product Vision:** *Transform 360° property captures into intelligent, explorable 3D experiences where every space has a story and every question leads to a more informed decision.*