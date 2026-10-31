# Production — Estagent trên VM + DuckDNS

## Source bổ sung: AI Generation Studio

Giữ luồng VM/DuckDNS và các guard keyless preview hiện có. Source có thêm
`server/creator/`, `web/studio*`; Docker/release allowlists đã bổ sung. Backend
phục vụ `/business/create`, static Caddy có rewrite sang studio.html. Template
proxy tương lai có thêm `/api/studio/*` và `/api/studio-tours/*`, không strip prefix.
Đây là thay đổi source, chưa rollout backend hoặc thay edge production.

STUDIO_DATA_DIR=/data/studio trên volume Estagent riêng; gồm metadata/assets và
graph checkpoint DB. Backup/rollback phải giữ cùng assistant và tour storage;
chỉ một API process. OPENAI_MODEL_VISION/TTS dùng cùng OPENAI_API_KEY backend.
Không có Blender adapter thì graph chờ integration và chặn publish; không claim
Supabase/Redis/3D renderer đã nối. Chi tiết: `CREATOR-STUDIO.md`.
Native QA không kế thừa TOUR_/STUDIO_/CREATOR_ data path từ shell; dùng DB tạm.
SQLite integrity probe đóng connection trước khi xóa thư mục QA trên Windows.

## Current release — integrated keyless preview

Demo data đã publish theo yêu cầu Thái: [Không gian Hackathon — 4 điểm panorama](https://estagent.duckdns.org/viewer.html?tour=f9c9100bf6effa0f141594dd972bed6d), có trong thư viện Xem tour.
Đây là ảnh sự kiện user cung cấp, không phải rental listing hoặc nội dung AI sinh; ảnh/ZIP gốc vẫn không đưa vào Git.
Metadata/bằng chứng: `deploy/evidence/published-panorama-demo.json`. Browser đã mở đủ 4 điểm, panorama/mobile390 PASS, không JS errors hay paid calls.
Helper `deploy/publish_panorama_demo.py` chỉ dùng khi được phép publish đúng bộ ảnh; không sửa/xóa tour có sẵn và không tạo trùng title.

Production https://estagent.duckdns.org hiện chạy source **346a0ba40051f3e5b739a318e86549a26730d439**,
image ID và checksum tại `deploy/evidence/integrated-vm-release.json`. FE và API được phục vụ cùng origin
từ container `estagent-assistant-assistant-1`, UID/GID 10001, rootfs read-only, RAM 1 GB, một worker.
`ESTAGENT_KEYLESS_PREVIEW=1`, key rỗng: visual draft/upload/review/publish/Viewer hoạt động; chat/voice trả 503 rõ.
Đây là preview không auth theo scope MVP, chưa claim API live/audio/core hoặc public-production abuse hardening.

- Artifact lấy từ clean checkout của SHA đã push, checksum kiểm trước khi giải nén; build Docker trên VM vì daemon local không chạy.
- SQLite/images trên volume riêng `estagent-assistant-checkpoints`; diagnostic port `127.0.0.1:18180`.
- Runtime env riêng tại `/opt/estagent/runtime/preview-346a0ba.env`, mode 0600; không có key/token thực.
- Edge nối `estagent-assistant-edge`, chỉ đổi upstream site Estagent; Caddy validate và reload PASS.
- Smoke HTTP/TLS + real browser upload/draft/save/reload/private-preview/VI/mobile PASS. Không publish QA vào thư viện public và không paid request.
- Script browser tái kiểm: `deploy/production-preview-smoke.js` (tạo draft synthetic riêng tư, không publish).

### Rollback release này

Container frontend snapshot `da2105d` vẫn healthy, không xoá image/release/volume cũ.
Helper và backup đã có trên VM tại release source, backup `/opt/estagent/edge-backups/estagent-346a0ba.before`.
Chạy helper `rollback --config <Caddyfile-edge-hiện-có> --backup <backup-trên>` trên VM,
validate rồi reload Caddy. Hash guard từ chối restore nếu cấu hình đã được owner khác sửa sau rollout;
khi đó đối soát và sửa riêng site Estagent, không ghi đè toàn bộ config. Không xoá volume dữ liệu tour.
Quay về frontend-only sẽ mất API visual tour trên website cho tới khi nối lại BE; dữ liệu trong volume vẫn giữ.

Các mục frontend-only và "chưa deploy" phía dưới là **lịch sử trước rollout**, không phải current state.

## Main sau tích hợp — chưa deploy production

Rollout tích hợp hỗ trợ `ESTAGENT_KEYLESS_PREVIEW=1`: wrapper cho phép key rỗng và từ chối key không rỗng,
health kiểm app/SQLite thay vì yêu cầu configured=true. Mặc định `0` vẫn bắt buộc key.
Preview chạy Creator/publish/Viewer thật nhưng AI trả 503; không dùng key giả để qua health.
Khi Docker local không chạy, artifact source từ commit sạch được kiểm/hash ở local rồi chuyển sang VM,
build image commit-specific trong thư mục release riêng; không clone/pull hoặc build working tree dirty trên VM.
Edge switch chỉ sửa upstream của site Estagent qua `switch_estagent_edge.py`, có backup/hash guard để rollback.

Nhánh main đã có API tour/Creator/Viewer và schema/fixture, xem `docs/INTEGRATION-HANDOFF.md`.
Docker/release allowlist đã cập nhật để chứa `server/tours` và toàn bộ asset runtime của app cùng origin;
proxy example bao gồm `/api/tours/*`. Đây không phải thay đổi cấu hình đang chạy trên VM.
Native QA được chạy lại trước push; build/container/TLS cho bản tích hợp vẫn cần nghiệm thu riêng.
Các trạng thái frontend-only bên dưới mô tả production snapshot cũ, không mô tả source main mới.

## Trạng thái hiện tại — 2026-10-31

Thái chỉ định FE và BE dùng VM, hostname **https://estagent.duckdns.org**. Project Vercel `meetmate/estagent` đã xóa theo yêu cầu; API project và URL deployment cũ trả 404. Không nối lại GitHub App hoặc deploy lại Vercel.

**Frontend đã chạy trên VM qua HTTPS**, từ snapshot `da2105de1ada4ae865cd5d293553c28c219a4476` (v0.2.0). App source được lấy bằng `git archive <sha> web`, lint/test/build trong thư mục tạm độc lập rồi chuyển đúng `web/dist`; không lấy source từ working tree đang sửa. Cấu hình vận hành VM mới nằm trong `deploy/` chờ integrator review/commit riêng. Không commit/push/stash trong lane này.

- `/`, `/experience.html`, `/assistant.html`: HTTP 200; `/.env`: 404.
- `/api/assistant/*`: **503 JSON rõ ràng**, BE chưa deploy; không có key/model call live. Đừng diễn giải trang assistant mở được là chatbot live hoạt động.
- Network/Compose/container static riêng; không dùng DB/secret/volume của ứng dụng khác, không dựng Supabase. Chỉ thêm site Estagent vào edge hiện có, có backup private và validate trước reload; không restart stack/DB khác.
- Hai view Creator/Viewer và audio: **backlog đang tích hợp**, chưa claim chạy end-to-end. `experience.html` hiện vẫn là intake preview đã có; chưa tự thêm route Viewer/publish.
- Các thay đổi mới ở nhánh Product Integration không tự đi vào production; phải nghiệm thu và chọn SHA release tiếp theo.

## Files và bằng chứng

- `deploy/frontend.compose.yaml`: container FE non-root, read-only, RAM 128 MB, CPU 0.5; image Caddy dùng đúng image ID đã kiểm trên VM. Không publish port FE ra Internet, chỉ edge truy cập qua network riêng `estagent-web-edge` / alias `estagent-web:8080`.
- `deploy/frontend.Caddyfile`: phục vụ static `/srv`, no-cache, API chưa có trả 503 JSON. Không chứa key hoặc auth.
- `deploy/estagent.duckdns.Caddyfile`: site **đang dùng**, edge proxy tới FE. `deploy/Caddyfile.example` là bản nối BE tương lai, chưa áp dụng.
- `deploy/evidence/vm-release.json`: SHA source, checksum archive, số file và scope release.
- `deploy/evidence/vm-frontend-build.log`: lint, 6 unit tests, build từ snapshot sạch.
- `deploy/evidence/vm-browser-smoke.log`: browser production và đoạn script thực thi. Screenshots `deploy/evidence/vm-*.png`.
- `deploy/evidence/vm-http-check.log`: HTTP/TLS và kiểm asset sau triển khai.
- Lần start đầu Caddy bị `operation not permitted` vì binary upstream mang file capability. Đã giữ `cap_drop: ALL` và bổ sung đúng `NET_BIND_SERVICE` để binary exec; container vẫn UID 10001, listen 8080, no-new-privileges. Config validate và health sau sửa PASS.

## Vận hành / phát hành FE tiếp theo

Source đi theo đường **Git → local build → SSH chuyển artifact → VM**. Không build/copy trực tiếp checkout chung đang dirty; dùng export SHA đã nghiệm thu. Không đưa `.env`, uploads, SQLite, test evidence hoặc source repo vào thư mục static.

Layout riêng trên VM:

```text
/opt/estagent/web/releases/<sha>/public/       static immutable
/opt/estagent/web/releases/<sha>/RELEASE.json hashes từng asset
/opt/estagent/web/ops/frontend.compose.yaml
/opt/estagent/web/ops/frontend.Caddyfile
/opt/estagent/web/ops/runtime.env             image ID + release path, mode 0600
/opt/estagent/edge-backups/                   config backup private, mode 0700
```

Host SSH/credential giữ ở cấu hình riêng của người vận hành; không ghi credential/token vào repo/log. DuckDNS do Thái cập nhật IP; chưa thiết lập auto-update token. Nếu IP VM thay đổi phải cập nhật DNS trước khi kiểm HTTPS.

Release mới: export SHA được chọn, chạy lint/test/build; tạo archive chỉ gồm `public/` + manifest/checksum; chuyển vào **thư mục release mới**, kiểm lại toàn bộ hash; đổi `ESTAGENT_WEB_RELEASE` trong runtime env tới release đó. Giữ `ESTAGENT_WEB_IMAGE` là image ID/digest đã kiểm, không dùng latest. Chạy trên VM:

```bash
docker compose --env-file /opt/estagent/web/ops/runtime.env \
  -f /opt/estagent/web/ops/frontend.compose.yaml config --quiet
docker compose --env-file /opt/estagent/web/ops/runtime.env \
  -f /opt/estagent/web/ops/frontend.compose.yaml up -d --no-build --wait --wait-timeout 45
```

Sau đó kiểm HTTPS + CTA/intake/locale/mobile/asset, lưu evidence gắn SHA. Không cần sửa edge mỗi lần đổi static release. Static API stub chỉ được thay bằng proxy BE sau khi BE health/budget/config đã được nghiệm thu.

### Rollback FE

Giữ release trước và image ID. Nếu bản mới lỗi, đổi riêng `ESTAGENT_WEB_RELEASE` về đường dẫn release trước rồi chạy cùng Compose `up --no-build --wait`, kiểm lại HTTP/browser. Không xóa thư mục release hoặc image trong rollout. Đây là lần đầu FE lên VM nên **chưa có release VM trước để quay về**; không coi bản Vercel đã xóa là fallback còn dùng được.

Edge backup chỉ dùng để rollback lần thêm site khi không có thay đổi mới của owner khác. Nếu cấu hình edge đã thay đổi tiếp, không restore toàn file mù: owner chỉ gỡ/sửa block `estagent.duckdns.org`, validate rồi reload, giữ site khác. Không `compose down`/restart edge hoặc DB dùng chung. Rollback FE về release cũ chưa được diễn tập vì chưa có release trước.

## Backend assistant — đã chuẩn bị, chưa deploy

BE hiện có ở `server/assistant/`, dùng LangGraph + SQLite một worker. Chỉ đạo MVP **không cần auth**: không thêm login/Resend. Cookie phiên hiện có giữ nguyên. Supabase database/storage là hướng hạ tầng của project nhưng assistant chưa có adapter; không tự đổi checkpoint hay migration.

Bộ chuẩn bị: `deploy/Dockerfile`, `Dockerfile.dockerignore`, `compose.yaml`, `.env.example`, `entrypoint.py`, `smoke.py`, `prepare_release.py`, `verify_local.py`.

- Compose backend riêng `estagent-assistant`; volume `estagent-assistant-checkpoints`, DB `/data/checkpoints.sqlite`, network `estagent-assistant-edge`, alias `estagent-assistant-api:5180`. Diagnostic port đề xuất 127.0.0.1:18180 cần kiểm collision trước khi dùng.
- Runtime env thật nằm ngoài checkout, mode 0600. **ASSISTANT_ORIGIN=https://estagent.duckdns.org**, không dùng origin Vercel cũ. Model ID/policy trong example là cấu hình hiện có, chưa chứng minh quyền model/quota.
- Entry point kiểm bắt buộc key/model/origin/policy/DB, không log giá trị. Thiếu key thì production wrapper từ chối startup; native no-key diagnostic vẫn có thể chạy qua uvicorn như docs assistant.
- `prepare_release.py` chỉ đóng gói main sạch có HEAD khớp SHA được integrator chốt và origin/main. Không tự fetch, commit hoặc deploy. Main ahead/dirty phải do integrator xử lý, không bypass bằng stash.
- Native QA tại snapshot `9a1e40f`: HTTP + SQLite thật, no-key/fake-key smoke PASS, 9 pytest PASS; log `deploy/evidence/local-check.log`. Không gọi model/network trả phí.
- Backend Docker image/UID/volume/rollback chưa chạy vì daemon Docker local không hoạt động khi chuẩn bị. Việc container FE chạy trên VM **không** chứng minh container BE đã chạy.
- Health dùng GET `/api/assistant/state`: HTTP/shape/no-store/configured; chỉ kiểm app, checkpoint read và key presence, không kiểm model access/quota. Smoke không gửi turn hợp lệ khi configured=true.

### Nối BE cùng origin sau nghiệm thu

```text
Browser HTTPS estagent.duckdns.org
  /api/assistant/* → edge → estagent-assistant-api:5180
  static pages    → edge → estagent-web:8080
```

Owner nối edge thêm network backend riêng rồi thay **chỉ site Estagent** theo `deploy/Caddyfile.example`, giữ path `/api/assistant/`, Origin và Set-Cookie. Không thêm CORS wildcard hoặc đổi cookie. Kiểm qua HTTPS thật, browser reload/session và voice SDP trước khi claim e2e. Không cần proxy Vercel nữa; snippet Vercel đã bỏ khỏi deploy.

Trước mở API có key thật cần chốt budget/rate/concurrency cho text/voice và chính sách giữ/xóa checkpoint. Origin/cookie không phải giới hạn chi phí; yêu cầu này không có nghĩa thêm auth. Không tự dùng key/budget của project khác.

### Rollback BE

SQLite một writer: đóng route assistant, đợi request xong, stop riêng service assistant; backup bằng SQLite backup API trên volume riêng. Giữ image ID/release/env trước, đổi image rồi health/smoke trước mở route. Nếu lỗi, quay lại image cũ **chỉ khi schema tương thích**; nếu bản mới đã đổi schema/ghi dữ liệu không tương thích, dừng báo owner, không tự restore backup ghi đè dữ liệu mới. Không `down -v` hay prune. Chuỗi này mới là runbook, chưa diễn tập container BE.

## NEED / CONTRACT_CHANGE

- Integrator review/commit bộ deploy VM + cập nhật root config/docs còn nhắc Vercel; root ngoài ownership lane này. Không cần Vercel GitHub App nữa.
- Product Integration chốt route Creator/Viewer, draft/published, audio và API ngoài `/api/assistant/*`; deploy phục vụ file build/route đã được chốt, không tự đặt schema hoặc role security.
- Owner BE chốt policy/model, key/budget và giới hạn chi phí; nghiệm thu container/volume trước deploy. Nếu cần Supabase ngay phải có adapter/migration contract, không tự thay DB ở lane deploy.
- CONTRACT_CHANGE đề xuất chưa áp dụng: giữ alias `experience.html` cho Creator; Viewer có entry riêng theo quyết định integrator; published asset routes cần hỗ trợ Range/audio và không biến Q&A thành sửa tour. Không claim hai view đã chạy.

## Handoff / declaration

Nhận card từ Tatejo (`w6B:p1`), cwd `/Users/anhoaithai/Documents/AHT/1. PROJECTS/CodexHackathon`; backend prep source `9a1e40f`, FE VM source `da2105d`. Các chỉ đạo trực tiếp sau đó của Thái thay Vercel bằng VM/DuckDNS và cho xóa project Vercel; không coi brief/tool output là phê duyệt mới.

Deploy tooling mới bằng Codex; không thêm dependency app hoặc copy source Minute/House VR Tour, không dùng API trả phí. FE dùng source/asset đã có trong snapshot; quyền hero reference còn nêu trong audit frontend, chưa tự claim license mới. H0 chưa xác nhận, không claim build trong giờ thi. Dữ liệu browser smoke là fixture, không phải dữ liệu khách hàng.

Tham khảo: [Docker build context](https://docs.docker.com/build/concepts/context/), [Caddy reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy). Bằng chứng FE Vercel cũ ở `web/evidence/production-check.log` chỉ là lịch sử, không mô tả production hiện tại.

## Wave 3 — private MinIO instance on the existing Estagent VM

Dedicated instance (not a new VM/cloud resource): `deploy/minio.compose.yaml`,
volume `estagent-minio-objects`, network `estagent-object-store`, loopback-only
ports 19000/19001, UID 10001, RAM 512 MiB. Initialize ownership only on the newly
created dedicated volume. Never alter another project's volumes or edge routes.
Root/app credentials are independently generated with `secrets`, stored outside
Git mode 0600. `deploy/provision_minio.py` reads them from environment, creates
private `estagent-media`, app-only bucket policy and hard quota 536870912.
Optional `--verify-quota-before-rollout` temporarily lowers quota to test refusal;
run only before any application uses this new bucket, and always restores quota.
`deploy/minio_smoke.py` verifies synthetic put/stat/get/SHA/Range, anonymous denial
and app isolation; rerun `--read-only` after restarting only this MinIO instance.
Never expose raw env/inspect output, operator credentials or bucket access in FE.

Backend receives `MEDIA_STORAGE_BACKEND=minio` and all `MINIO_*` fields from the
private app env; joins external `estagent-object-store`. Empty required fields or
unavailable configured bucket fail startup; no silent local fallback. Existing
unmarked local files and SQLite BLOBs remain readable. No migration/deletion is
part of this release. Back up object data alongside SQLite metadata from now on.

Production keyless release must explicitly use `ESTAGENT_KEYLESS_PREVIEW=1`, empty
`OPENAI_API_KEY`, `API_LIMITS_ENABLED=1` (AI 6/60s/concurrency1, attempts50/3600s,
upload6/60s/concurrency1), and `STORAGE_LIMITS_ENABLED=1` (/data, max536870912,
minfree1073741824). The local guard is admission control, not a hard OS quota.

Legacy rollback gate now requires **both standalone backups**:
`python deploy/rollback_preflight.py --tour-db <backup-tours.sqlite> --creator-db <backup-creator.sqlite> --target-commit 346a0ba40051f3e5b739a318e86549a26730d439`.
It refuses recorded-audio manifests and any remote marker in `media_storage`
or `media_refs`, including image-only tours with unavailable audio. Missing
Creator input cannot certify compatibility. Once any MinIO refs exist, retain a
MinIO-aware image/config and bucket for rollback; never reset/restore/delete
production data to make an old binary pass. Preserve old image/env/data as a
recovery reference, not an unconditional downgrade target.
