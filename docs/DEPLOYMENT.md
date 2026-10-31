# Production — Estagent

## Handoff deploy vòng 1 — 2026-10-31

Nhận từ Tatejo (`w6B:p1`) qua brief điều phối; cwd `/Users/anhoaithai/Documents/AHT/1. PROJECTS/CodexHackathon`. Commit nguồn assistant kiểm chứng: `9a1e40f89e2afa1a5e0ec2671a21187ff4efe723`. Bộ deploy bên dưới là thay đổi chưa commit dành cho review. Phạm vi ghi: `deploy/`, file này và `status/web.md`. Không commit/push/stash/spawn hoặc deploy production trong vòng này.

**BE đã có trên main** tại `server/assistant/`; thông tin cũ “chưa có BE” không còn đúng. Backend hiện dùng LangGraph + SQLite, **một worker**. Supabase database/storage là định hướng hạ tầng đã được Thái nêu; assistant chưa có adapter Supabase. Không dựng Supabase, chuyển schema hay dùng DB/secret/volume của stack khác trong vòng này.

Chỉ đạo mới: **MVP chưa cần auth**. Cookie phiên hiện có giữ nguyên; không thêm login, Resend hay tài khoản. Nội dung yêu cầu auth production cũ trong `docs/ASSISTANT.md` cần owner cập nhật theo quyết định này.

## Trạng thái đã kiểm chứng

- Local Python 3.13.7 có đủ dependency để import assistant. `deploy/verify_local.py` chạy snapshot assistant đã commit trong thư mục tạm, không dùng code server đang được lane khác sửa.
- Native HTTP + SQLite PASS: state, cookie, wrong-origin 403, invalid turn 422, body >64 KB trả 413, không có key trả 503, đọc lại SQLite sau restart; 9 test assistant đã commit PASS, bao gồm persistence qua restart với extractor fixture.
- Hai mode native: không key và key **giả**. Không gửi request model hợp lệ, không kiểm OpenAI live/voice/quota/chất lượng câu trả lời. LangGraph/SQLite là thật, model/network trong pytest là fixture.
- Docker CLI/Compose có sẵn nhưng **daemon local chưa chạy**. `docker compose config --quiet` PASS với env fixture; chưa build/chạy image, chưa kiểm UID/volume/resource limit/TLS trong container.
- `prepare_release.py` từ chối checkout dirty với exit 2; chưa tạo artifact production. Nhánh `main` đang có thay đổi của nhiều lane; integrator là writer duy nhất cho Git.
- Vercel API đọc lại ngày 2026-10-31: project `estagent`, `link = null`. Không thử connect lại. Lỗi trước đó yêu cầu GitHub App cho repo mới vẫn chưa được chứng minh đã hết.
- Evidence: `deploy/evidence/local-check.log`, `deploy/evidence/preflight.log`.

Chạy lại native QA: `python3 deploy/verify_local.py`. Script tự tạo snapshot commit trong thư mục tạm, dùng SQLite riêng, chạy smoke/pytest rồi dừng đúng tiến trình của nó; không dùng real key hoặc data hiện có. Phần startup readiness dùng HTTP retry giới hạn 20 giây trong test harness, không poll job production.

## Frontend / Git

- Production hiện có: https://estagent-weld.vercel.app. Vercel team/project: `meetmate/estagent`.
- Origin: `https://github.com/PhuocDang2104/MLIoT_Estagent_Codex.git`; remote cũ chỉ để đối chiếu dưới tên `previous-origin`.
- Vercel auto-deploy Git đang ngắt. Chủ repo cần cấp quyền [Vercel GitHub App](https://github.com/apps/vercel); chỉ thử connect lại sau khi có bằng chứng quyền đã được cấp.
- Sau khi quyền có: `vercel git connect https://github.com/PhuocDang2104/MLIoT_Estagent_Codex.git --yes --scope meetmate`, rồi đọc lại link. CLI deploy vẫn dùng được nhưng chỉ từ commit sạch đã nghiệm thu.
- Root `vercel.json`, web build/package thuộc owner khác; vòng này chỉ cung cấp snippet `deploy/vercel-rewrites.example.json` để review, chưa sửa route.

## Release riêng: Git → local → VM

Files: `deploy/Dockerfile`, `Dockerfile.dockerignore`, `compose.yaml`, `.env.example`, `entrypoint.py`, `smoke.py`, `prepare_release.py`.

- Image base Python 3.13 slim; cài đúng `server/assistant/requirements.txt`, không thêm dependency. Base tag và transitive dependencies chưa khóa digest; sau build phải lưu image ID + checksum image tar để deploy/rollback đúng artifact, không rebuild để rollback.
- Runtime UID/GID 10001, một uvicorn worker trên 5180, không access log; filesystem read-only + tmpfs `/tmp`, giới hạn RAM/CPU/log. Đây là cấu hình đề xuất chưa đo trong container.
- Compose project `estagent-assistant`; volume **riêng** `estagent-assistant-checkpoints`, DB `/data/checkpoints.sqlite`; network riêng `estagent-assistant-edge`, alias API `estagent-assistant-api`. Không dùng volume external của project khác.
- Diagnostic port đề xuất `127.0.0.1:18180` trên VM. Phải kiểm port còn trống và tên namespace chưa thuộc workload khác trước lần tạo đầu; chưa kiểm collision trong vòng này.
- `.env.example` chỉ có placeholder/default có tài liệu. Real runtime env nằm ngoài checkout, mode 0600. Không `cat .env`, `docker inspect .Config` hoặc `compose config` không có `--quiet` vào log vì có thể lộ key.
- Entry point từ chối thiếu key/model/origin/DB/policy, placeholder, origin không HTTPS, field policy không thuộc vocabulary app và DB path không ghi được. `--check-config` chỉ kiểm format/presence, không xác thực key/model/quota.
- `ASSISTANT_REQUIRED_FIELDS=address,area,bedrooms` giữ đúng policy **tạm** hiện có, chưa coi là quyết định sản phẩm. Owner phải chốt trước production; deploy không tự đặt field mới.

Các lệnh sau dành cho **integrator sau nghiệm thu**, chưa chạy production trong vòng này:

```bash
# Tại checkout main sạch, đồng bộ origin/main trước; không stash thay đổi của lane.
git fetch origin
git pull --ff-only origin main
# Chạy gate và review các lane theo docs/LANE-DISPATCH.md.
ESTAGENT_COMMIT=$(git rev-parse HEAD)
python3 deploy/prepare_release.py --commit "$ESTAGENT_COMMIT" --out-dir /tmp/estagent-releases
# Artifact chỉ lấy allowlist từ commit, không copy working tree/secret/database.
cd /tmp/estagent-releases
shasum -a 256 -c "estagent-assistant-$ESTAGENT_COMMIT.tar.gz.sha256"
mkdir "build-$ESTAGENT_COMMIT"
tar -xzf "estagent-assistant-$ESTAGENT_COMMIT.tar.gz" -C "build-$ESTAGENT_COMMIT"
cd "build-$ESTAGENT_COMMIT"
# ESTAGENT_PLATFORM phải dựa trên kiến trúc VM đã kiểm (không đoán từ máy Mac).
docker buildx build --platform "$ESTAGENT_PLATFORM" --load \
  -f deploy/Dockerfile -t "estagent-assistant:$ESTAGENT_COMMIT" .
docker image inspect "estagent-assistant:$ESTAGENT_COMMIT" --format '{{.Id}}'
docker save -o "../image-$ESTAGENT_COMMIT.tar" "estagent-assistant:$ESTAGENT_COMMIT"
shasum -a 256 "../image-$ESTAGENT_COMMIT.tar"
```

Chuyển archive nguồn + checksum + image tar/ID từ local qua SSH vào thư mục release **mới** `/opt/estagent/releases/<sha>`; host/credential lấy từ cấu hình riêng của owner, không ghi vào repo. Kiểm checksum trên VM rồi `docker load`. Không clone/pull từ VM và không ghi đè release trước. Chưa cung cấp script tự SSH/up để tránh kích hoạt production trong vòng chuẩn bị.

Real env đề xuất `/opt/estagent/runtime/assistant.env`; `ASSISTANT_IMAGE=estagent-assistant:<sha>` phải khớp image đã kiểm. Sau kiểm port/namespace và budget, owner chạy từ thư mục release:

```bash
docker compose --env-file /opt/estagent/runtime/assistant.env -f deploy/compose.yaml config --quiet
docker compose --env-file /opt/estagent/runtime/assistant.env -f deploy/compose.yaml up -d --no-build --wait --wait-timeout 60
python3 deploy/smoke.py --base-url http://127.0.0.1:18180 --origin https://estagent-weld.vercel.app
```

Health dùng `GET /api/assistant/state` hiện có: HTTP 200, shape cơ bản, no-store, `configured=true`; kiểm được app/SQLite/key presence, **không** chứng minh key/quota/model hoạt động. Health không giữ cookie hay ghi profile. Dedicated `/healthz` có thể được owner BE bổ sung sau, không phải endpoint đã có.

## HTTPS / proxy FE đề xuất

Khuyến nghị một public hostname BE dưới domain đội kiểm soát, dạng `assistant-api.<domain-đã-chốt>`. Không đoán domain hay tự đăng ký DNS.

```text
Browser: https://estagent-weld.vercel.app/api/assistant/*
  → Vercel external rewrite, giữ nguyên path
  → https://<API_HOST>/api/assistant/*
  → edge Caddy trên network riêng
  → estagent-assistant-api:5180
```

- `deploy/Caddyfile.example` là **snippet** cho owner edge: chỉ expose `/api/assistant/*`, không strip prefix; các path khác 404. Caddy container hiện có cần được owner nối vào network `estagent-assistant-edge` và validate/reload đúng cấu hình của nó. **Không** thay toàn bộ Caddyfile hoặc chạy `compose down` stack dùng chung. Nếu edge chạy trong container, `127.0.0.1:18180` trong Caddy là chính container edge, không phải VM host; vì vậy dùng network alias ở trên.
- Owner root tích hợp snippet rewrite sau khi hostname/TLS được xác minh. `ASSISTANT_ORIGIN` vẫn là **origin FE canonical**, không phải hostname BE. Giữ `Origin`, `Set-Cookie` và path `/api/assistant/`; cookie Secure/HttpOnly/SameSite=Strict thuộc origin FE khi đi qua proxy. Preview origin khác sẽ bị 403 theo contract hiện tại.
- Chạy smoke cả trực tiếp BE và xuyên qua FE sau integration. Cần kiểm browser reload/khôi phục cookie + voice SDP qua proxy; vòng này chưa chứng minh hành vi proxy thật.
- Không thêm login theo chỉ đạo MVP. Origin/cookie không phải cơ chế giới hạn chi phí: trước mở API có key thật, owner cần budget/rate/concurrency limit phù hợp cho text/voice và chốt chính sách giữ/xóa checkpoint. Đây là NEED về vận hành, không được diễn giải thành yêu cầu auth mới.

## Rollback — chỉ service Estagent

Đề xuất rollout có khoảng dừng ngắn vì SQLite một writer; **không blue/green hai bản cùng ghi một volume**.

1. Giữ release trước gồm source SHA, archive checksum, immutable image ID/tag, cấu hình không chứa secret và vị trí env riêng. Không xóa image/volume trong rollout.
2. Trước đổi image: dừng nhận request cho route assistant, đợi request đang chạy hoàn tất rồi stop **service assistant của project estagent-assistant**. Backup checkpoint bằng SQLite backup API từ đúng volume riêng (không copy mù file đang ghi/WAL). Owner giữ backup ở vùng private; không đưa vào artifact/log/repo.
3. Chạy image mới, `--wait` và smoke local. Chỉ mở lại route khi PASS. Giữ nguyên cookie name/path và env/policy tương thích.
4. Nếu FAIL: giữ route đóng, stop image mới; chạy lại **image ID/tag cũ đã giữ** với Compose của release cũ và volume Estagent. Không `down -v`, không prune, không restart edge/DB khác. Chạy health + smoke trước khi mở route.
5. Nếu version mới đã đổi SQLite schema hoặc ghi dữ liệu không tương thích: **dừng và báo owner**, không tự restore backup ghi đè dữ liệu phát sinh. Restore/migration cần quyết định dữ liệu riêng; không giả định đổi image là rollback được DB.

Sau khi owner xác nhận schema còn tương thích và image cũ khớp ID đã giữ, lệnh đổi lại service (không tự chạy trong vòng này):

```bash
# ESTAGENT_PREVIOUS_COMMIT là SHA đã nghiệm thu trước đó; image phải còn local.
ASSISTANT_IMAGE="estagent-assistant:$ESTAGENT_PREVIOUS_COMMIT" \
  docker compose --env-file /opt/estagent/runtime/assistant.env \
  -f "/opt/estagent/releases/$ESTAGENT_PREVIOUS_COMMIT/deploy/compose.yaml" \
  up -d --no-build --wait --wait-timeout 60
python3 "/opt/estagent/releases/$ESTAGENT_PREVIOUS_COMMIT/deploy/smoke.py" \
  --base-url http://127.0.0.1:18180 --origin https://estagent-weld.vercel.app
```

Container/volume và chuỗi rollback này **chưa chạy thật** do Docker daemon local chưa chạy. Chỉ native restart + persistence fixture được kiểm. Owner cần diễn tập bằng volume QA riêng trước production; không dùng volume production để diễn tập.

## NEED trước vòng triển khai

- Integrator nghiệm thu/commit các lane rồi cung cấp SHA sạch; cập nhật hai dòng “chưa có BE” cũ trong root `AGENTS.md` (ngoài Paths vòng này).
- Máy có Docker daemon để build/run/health/UID/volume/restart/rollback với volume QA riêng; ghi image ID và xác nhận kiến trúc target. Chưa cần thêm dependency app.
- Owner chốt API hostname/DNS/TLS; owner edge review network + Caddy snippet, owner root tích hợp rewrite/build assistant assets. Không có thay đổi root/server/web trong vòng này.
- Owner chatbot cập nhật phần auth cũ trong `docs/ASSISTANT.md`, xác nhận required fields và cấu hình model thực; cấp key/budget ở môi trường private và kiểm text/voice live riêng.
- Chủ repo cấp GitHub App cho Vercel; auto-deploy chưa nối. Không coi quyền GitHub WRITE là quyền GitHub App.
- Nếu yêu cầu dùng Supabase cho checkpoint ngay vòng tới: cần contract + adapter/migration do owner BE chốt; không tự thay SQLite trong deploy.

## Declaration / nguồn

Deploy tooling viết mới bằng Codex ngày 2026-10-31 từ contract/source assistant hiện có; không copy code Minute/House VR Tour, không thêm package app, không gọi model/dịch vụ trả phí. Docker/Python/Compose/Vercel/Caddy là công cụ hạ tầng; package versions giữ nguyên requirements owner BE. Asset/font đi kèm assistant lấy từ repo sẵn có, license/declaration thuộc `web/README.md` và `web/assets/SOURCES.md`; chưa xác minh quyền mới. H0 chưa xác nhận, không claim build trong giờ thi.

Tham khảo chính thức: [Docker build context / Dockerfile-specific ignore](https://docs.docker.com/build/concepts/context/), [Vercel rewrites](https://vercel.com/docs/routing/rewrites), [Caddy reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy). Đề xuất mạng/proxy ở trên suy ra từ layout VM đã khảo sát và contract cookie/origin của app, chưa kiểm TLS end-to-end.

## Lịch sử: bằng chứng FE deploy trước vòng này

- `bash scripts/gate.sh all`: FE lint/build PASS; core, AI, contract SKIP vì chưa có implementation/fixture.
- `bash scripts/gate.sh all --strict`: FAIL do những SKIP trên; chưa đủ điều kiện tuyên bố sản phẩm end-to-end hoàn tất.
- Production `/`, `/experience.html`, `/assets/hero.jpg`: HTTP 200; `/AGENTS.md`: 404.
- Playwright production PASS: CTA, chọn ảnh, xem/xóa/clear, từ chối ảnh lỗi, menu mobile và không tràn chiều ngang 320/390px; không có browser errors.
- Log kèm script thực thi: `web/evidence/production-check.log`; screenshots `web/evidence/prod-*.png`.
- Lần chạy browser đầu timeout vì chọn file trước khi trang tải xong; thêm `waitForLoadState('load')` sau CTA trong test rồi chạy lại PASS, không sửa app.
- BE/DB Estagent chưa triển khai; mới kiểm SSH và tài nguyên VM, không thay đổi các stack hiện có. Chưa có review độc lập khác provider.
