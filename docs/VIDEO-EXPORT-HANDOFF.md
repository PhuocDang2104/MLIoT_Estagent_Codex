# VIDEO EXPORT — handoff cho Tatejo và Deploy

## Cập nhật ưu tiên cho Deploy

Coordinator đã duyệt **VIDEO_EXPORT_RENDERER=ffmpeg**; đọc mục P0 cuối file cho runtime Linux
768MiB đã probe. Các yêu cầu Node/Chrome/2GiB bên dưới chỉ còn áp dụng cho mode HyperFrames.

## Kết luận

**PARTIAL: capability local đã xuất/phát MP4 thật; production chưa được nghiệm thu.**
Feature mặc định tắt, không chặn rollout Viewer + MinIO. Strict gate vẫn core SKIP baseline.
Không merge/push/deploy; không sửa main, Viewer immersive, object_storage.py, app.py hay package/build.

- Nhận từ Tatejo, trong scope Thái giao; card `docs/work-items/VIDEO-EXPORT.md`.
- Cwd: `/Users/anhoaithai/Documents/AHT/1. PROJECTS/CodexHackathon/.worktrees/video-export`.
- Branch `feature/video-export`, base `6c50572344930f338b83517c908b88edf05dd8f1`
  (HEAD integration/wave2-release tại lúc tạo worktree).
- SHA implementation/evidence: **`dc3784b07ff0bf169e5afa80caad2fc31d911ef6`**; commit handoff kế tiếp chỉ sửa tài liệu.
- File chính: `server/exports/{api,plan,render}.py`, `web/export.{html,js,css}`;
  `server/tours/api.py` chỉ thêm install hook, `web/creator.js` chỉ thêm entry sau publish.
- Bối cảnh E2E ZIP/ZInD/PanSplat chỉ là thông tin điều phối. Không đọc/import ZIP, ảnh thật,
  cached MP4/GLB hoặc dùng public demo không thuộc cookie để vượt kiểm owner. Không claim
  ảnh → 3D/video model mới; quyền export dữ liệu thật vẫn chưa chốt bởi lane này.

## Luồng đã triển khai

Creator publish → entry **Xuất video** → chọn OWNED published checkpoint snapshot → dọc/ngang
→ storyboard nội dung/khung hình/audio state → tạo job → kiểm trạng thái → phát/tải MP4 riêng tư.
Preview trước job là storyboard tĩnh có source captions và audio disclosure, chưa phải player
đầy đủ của composition. Video hoàn tất mới có motion/audio phối để kiểm trực tiếp.

Nguồn duy nhất là `published.doc`, owner xác minh bằng JOIN `published.draft = drafts.id` và
`drafts.owner = hash(cookie)`. Không đọc nội dung draft đang sửa. Bắt đầu tại `start_scene_id`
đã duyệt rồi đi theo thứ tự scenes, vòng một lượt. Metadata job giữ bản sao snapshot và edit plan;
không thay schema hoặc bytes/ref publication. Default 720p/24fps chỉ là cấu hình prototype,
không đưa lựa chọn kỹ thuật này vào flow người dùng.

- Dọc 720×1280: crop giữa + pan ngang chậm; ngang 1280×720: crop + pan dọc/zoom nhẹ.
- Title và scene name dùng nội dung đã publish; captions là transcript nếu có, nếu không dùng
  description, tối đa 160 ký tự với dấu … và disclosure excerpt. Không transcription/translation.
- Mỗi scene 3s khi không có lời; có lời: `max(3s, ceil((duration + .3s)*24)/24)`.
  Giữ đủ recording, không tự cắt lời. Tổng >180s từ chối 422; <=20 scene theo manifest hiện có.
- Nhạc loop PCM vào một bed hữu hạn để tránh bản thu 1 frame sinh hàng triệu audio nodes.
  Gain bed .25, xuống .05 trong đoạn lời, khôi phục sau lời. Bản thu theo source locale của snapshot.
  Không TTS/device speech, không claim giọng AI. Đây là volume duck MVP; chưa nghiệm thu spectral
  carve/chất lượng lời người thật. Không thêm dependency carve ngoài phạm vi.
- Hình ảnh là crop/pan của photo/panorama đã cung cấp, không tái dựng camera/3D hoặc đường nối phòng.

## API/ref chính xác để root nối doc E2E

Cookie giữ nguyên `estagent_tours`, path `/api/tours/`; write vẫn cần exact Origin.
Không token/public bucket URL mới, không browser-owned metadata/quota.

| Endpoint | Hành vi / shape |
|---|---|
| `GET /api/tours/exports/sources` | Owner-only; `{enabled, items:[{id,title,revision,locale}]}` từ publication thuộc draft của cookie |
| `GET /api/tours/exports/preview/{tour_id}?aspect=portrait\|landscape` | Owner-only edit plan: `tour_id,title,locale,aspect,width,height,duration,scenes,music,audio_status,notice`; mỗi scene thêm `start,duration,narration` |
| `POST /api/tours/exports` | `{tour_id:hex32, aspect:portrait\|landscape, request_id:[A-Za-z0-9-]{8,80}}`; extra fields bị từ chối |
| `GET /api/tours/exports/{job_id}` | Own job; `{id,state,stage,error,aspect,download}` |
| `GET /api/tours/exports/{job_id}/download` | Own ready MP4; `video/mp4`, Range 206/416; chưa ready 409 |

POST trả cùng job shape với GET. `download` null cho tới ready; sau đó là
`/api/tours/exports/<job_id>/download`, không phải object key hoặc presigned URL.

- State: **queued → rendering → ready/error**. Stage phản ánh việc thật: `queued`, `reading-source`,
  `renderer-running` (check/render), `storing-private-output`, `complete`, `failed`, `interrupted`.
  Không fake percentage. UI dùng nút kiểm trạng thái, không tự poll hoặc tự retry render.
- Preview `audio_status`: `complete` = đủ lời đúng locale cho mọi scene; `partial` = có nhạc/lời
  nhưng thiếu lời một số scene; `silent` = không có track. Không thay `manifest.audio.status` cũ.
- Missing cookie 401; other-owner source/job 404. Same owner+request_id+body trả cùng ID kể cả
  job error; đổi body cùng ID 409. Explicit retry cần request_id mới; thất bại vẫn tính allowance.
- Public Viewer vẫn read-only. Public demo không xuất hiện trong sources nếu không có cookie chủ.

## Worker, persistence, storage và config

`video_exports` additive table trong `<TOUR_DATA_DIR>/tours.sqlite`:
`id,owner,request_id,body,snapshot,edit,state,stage,error,created,backend`;
`UNIQUE(owner,request_id)`. Không đổi hoặc migrate record cũ/production.

- Một renderer qua file lock service-wide trên export directory; SQLite `BEGIN IMMEDIATE`
  serialize admission. Tối đa **2 tổng queued+rendering**, rolling 24h global12 và owner4,
  tính từ metadata persisted. Đổi cookie/restart không reset global allowance.
- Startup enabled kiểm lock và đổi pending job sang error/interrupted; không tự chạy lại.
  Metadata/output ready tồn tại qua restart. Không tự garbage collect publication hoặc output.
- CLI argv cố định, không shell/eval/model-generated command. Text HTML-escaped; ID hex32;
  source media đọc file nội bộ hoặc MinIO SDK theo marker/namespace server, không HTTP fetch URL.
- Mỗi job có thư mục tạm riêng, dọn sau success/error. Check timeout60s, render180s, ffprobe15s;
  timeout terminate rồi kill process group nếu cần. Output cap50 MiB. Renderer/check logs private
  được giữ theo job; API trả lỗi gọn không log credentials/cookie/media bodies.
- `VIDEO_EXPORT_ENABLED=0` mặc định: không tạo bảng/worker export; GET sources/preview vẫn cho
  owner xem. POST disabled 503. Bật `1` yêu cầu absolute file `VIDEO_EXPORT_HYPERFRAMES` và
  node/ffmpeg/ffprobe trong PATH, thiếu config/binary báo ValueError rõ khi startup.
- `VIDEO_EXPORT_LOCAL_QA=1` chỉ prototype: MP4 dưới `<TOUR_DATA_DIR>/exports/<job_id>.mp4`.
  Mặc định `0`: yêu cầu adapter MinIO có namespace exports; nếu chưa tích hợp từ chối 503,
  **không fallback local production**. Namespace dự kiến `tours/exports/<job_id>.mp4`.
- `app.state.close_video_exports()` có sẵn để dừng child processes khi shutdown. App lifecycle
  hiện tại chưa gọi nó; QA fixture có nối hook. Deploy phải áp patch lifecycle trước enable.
  Không claim hard-kill/power-loss cleanup hoặc multi-host renderer coordination đã nghiệm thu.

## Evidence đã chạy

Thư mục `tests/exports/evidence/`; không MP4/WAV/input PNG/DB/cookie/env được commit.

- `baseline-gate.log` và `final-gate.log`: web lint/test/build, AI compile/tests, contract PASS;
  strict exit1 duy nhất vì core SKIP. Không hạ gate. JS export được kiểm riêng bằng node --check
  vì root lint/build chưa thêm file mới.
- `export-tests.log`: **4 passed**, suite export actual API/SQLite/HyperFrames; không process mock/placeholder.
  Kiểm hai MP4, ownership, Range, idempotency/mismatch, publication hash immutable, draft sửa
  không đổi source, ready persistence, interrupted metadata, missing-source error, queue/owner/
  global admission, cookie rotation/restart, timeout cả child và WAV 1 frame bounded bed.
  Queue/history/crash states có fixture metadata; không gọi đó là render thành công.
- `exports.json`: portrait **720×1280**, landscape **1280×720**, mỗi file **6.000s**, **H.264 + AAC**.
- `hyperframes-checks.json`: actual check/lint/runtime/layout/contrast PASS; 25/25 text contrast
  ở mỗi composition đã kiểm. Motion sidecar audit không bật; motion được đo từ pixel output.
- `audio-analysis.json`: giải mã AAC thành PCM và đo 220/440/660 Hz: gain bed dưới lời/between
  = **0.200**, đúng voice frequency ở scene1/scene2, sai scene <5%. Đây là kiểm tone, không phải
  subjective listening hay chất lượng giọng người thật.
- `motion-analysis.json`: khác biệt pixel vùng ảnh .5s→2.5s, xác nhận chuyển động thật ở hai aspect.
- `browser.log`: Creator export UI chọn cả hai aspect → tạo job thực → phát HTMLVideoElement;
  time >.5s, đúng videoWidth/videoHeight/duration, Range download, zero page errors; mobile390px
  không overflow. Các screenshot `*-playback.png`, `*-scene-two.png`, `export-mobile.png` đã xem.
- `restart-browser.log`: **hai process HTTP khác nhau** đọc cùng private export; SHA256 bytes
  trước/sau giống nhau, state ready và browser phát được sau restart. Không render lại ngầm.
- `render-probe.log`: local probe ban đầu render thật; sandbox đầu tiên bị `uv_os_setpriority EPERM`.
  Đã chạy renderer với quyền local phù hợp; không đổi sang cloud. Probe static thiếu timeline có
  readiness warning; composition app dùng finite CSS + `data-no-timeline`, check/render sau PASS.
- Usage **unknown**: npx offline probe ENOTCACHED; cached CLI trả `usage_request_failed`.
  Không suy đoán allowance từ doctor. Doctor có Chrome/FFmpeg/node; optional Docker/TTS fail
  không được dùng làm lý do cài thêm dependency hoặc gọi paid provider.

## Lệnh tái lập và artifact

Có sẵn Python3.13/uv, playwright-cli+Chromium, cached/installed HyperFrames0.8.167, Node,
FFmpeg/ffprobe. Không dùng env/key production. Từ cwd worktree:

```bash
export VIDEO_EXPORT_HYPERFRAMES=/absolute/path/to/hyperframes/bin/hyperframes.mjs
export QA_OUTPUT_DIR=/private/tmp/estagent-video-export-new-run
uv run --quiet --python 3.13 --with pytest --with jsonschema --with-requirements server/assistant/requirements.txt python -m pytest -q tests/exports
uv run --quiet --python 3.13 --with pytest --with jsonschema --with-requirements server/assistant/requirements.txt python tests/exports/run_browser.py
QA_RESTART_ONLY=1 uv run --quiet --python 3.13 --with pytest --with jsonschema --with-requirements server/assistant/requirements.txt python tests/exports/run_browser.py
python3 tests/exports/check_audio.py "$QA_OUTPUT_DIR/portrait.mp4" "$QA_OUTPUT_DIR/landscape.mp4"
python3 tests/exports/check_motion.py "$QA_OUTPUT_DIR/portrait.mp4" "$QA_OUTPUT_DIR/landscape.mp4"
bash scripts/gate.sh all --strict
node --check web/export.js
git apply --check tests/exports/patches/deploy-owned.patch
python3 scripts/check_commit_attribution.py --all
```

Dùng scratch mới mỗi run để không vô tình chạm allowance của lần trước; không reset quota để QA xanh.
Output cuối để review local: `/private/tmp/estagent-video-export-final/{portrait,landscape}.mp4`.
Bằng chứng browser/restart dùng scratch synthetic `/private/tmp/estagent-video-export-reviewed`.
Các server/browser QA đã đóng; không gửi URL cổng tạm như một deployment còn sống.
Chạy thủ công local: `VIDEO_EXPORT_ENABLED=1 VIDEO_EXPORT_LOCAL_QA=1
VIDEO_EXPORT_HYPERFRAMES=<installed absolute CLI> bash scripts/dev.sh`, rồi
`http://127.0.0.1:5180/export.html` sau khi publish bằng cùng browser cookie.
UI chưa có history picker cho job; muốn truy lại qua API phải giữ job_id. Không claim full production UX.

## NEED cho Deploy — patch reviewable, chưa áp dụng

`tests/exports/patches/deploy-owned.patch` đã **git apply --check PASS** trên base worktree:

1. `server/object_storage.py`: whitelist `tours/exports/<hex32>.mp4` và `video/mp4`; giữ private
   bucket/immutable put/Range hiện có. Chưa kiểm real MinIO output, outage/full bucket hoặc VM.
2. `server/assistant/app.py`: gọi close_video_exports trong lifespan finally để terminate renderer.
3. `web/build.mjs`, `web/package.json`: copy export HTML/JS/CSS và lint JS mới.
4. Runtime/package chưa có patch OS-specific: Deploy cần duyệt/provision pinned HyperFrames0.8.167,
   Node>=22, Chrome headless, FFmpeg H.264/AAC/ffprobe; bundle server/exports và font hiện có.
   Không tự npm install/package/root/deploy trong lane này. Pins đã chạy trên macOS arm64:
   Node26.10.0, Chrome headless152.0.7977.30, FFmpeg8.0, ffprobe9.0.2, HyperFrames0.8.167.
   Linux/VM compatibility, peak RAM và CPU throughput chưa probe. App chưa có hard CPU/RAM cap.
   Đề xuất Deploy thử renderer budget2 vCPU/2 GiB bằng cgroup/container rồi đo; đây không phải
   mức đã nghiệm thu. Hiện background renderer ở cùng app process tree: isolation/cgroup riêng
   cần Deploy wiring; không áp cap mù lên service Viewer đang rollout. Giữ feature disabled
   nếu runtime/isolation chưa sẵn sàng, không đổi renderer trong lane này để chạy kịp deadline.

Khuyến nghị giữ HyperFrames cho prototype đã chạy được, chưa bật production trước khi Deploy kiểm
runtime + lifecycle + private MinIO. Nếu không muốn thêm Node/Chrome trên VM, **NEED coordinator
chốt hướng FFmpeg native** (fixed crop/motion/text/audio filters tái dùng plan/ownership/quota);
chưa triển khai hay lách skill bằng renderer thay thế. Export không phải blocker rollout hiện tại.

## Nguồn, quyền, mock/live, H0

- Code mới Codex-assisted dựa trên baseline repo và markup/runtime contract HyperFrames skills;
  không copy app từ reference repo. H0 unknown, không claim viết trong giờ thi.
- Installed HyperFrames0.8.167 package metadata: Apache-2.0, `heygen-com/hyperframes/packages/cli`;
  cached Chrome headless152.0.7977.30, Node26.10.0 trên máy QA. Không bundle binary trong commit.
- FFmpeg8.0 build `--enable-gpl --enable-libx264`; ffprobe9.0.2. Deploy cần giữ license phù hợp
  khi đóng gói binary. Không thêm Python/npm dependency vào root.
- Font tái dùng `web/assets/manrope-variable.ttf`, SIL OFL1.1 tại `Manrope-OFL.txt`.
- Fixtures: Python/Pillow vẽ ảnh hình học, stdlib wave tạo PCM tone 220/440/660 Hz.
  Không human VO, licensed music, ảnh nhà/private demo/ZIP/GLB/PanSplat cache.
- Audio rights/source là declaration trong snapshot, không xác minh độc lập quyền re-export.
  Đã chứng minh local composition → MP4 bằng renderer thật; không image→3D hay paid AI.
- HTTP/SQLite/WAV/H.264/AAC/HyperFrames/browser thật; crash/quota history metadata là fixture;
  MinIO production và subjective VO quality **chưa kiểm chứng**. `DO_NOT_TRACK=1` cho renderer;
  không gửi feedback/upload composition/provider/cloud render.

## P0 native FFmpeg follow-up — coordinator approved, 2026-10-31

Implementation + Linux evidence SHA: `85b3fb634515a556fc2d8193c2924fd0643925a5`; base `7797ef0`.

Coordinator đã chốt backend native để tránh Node/Chromium trên VM. Dùng
`VIDEO_EXPORT_RENDERER=ffmpeg`; default `hyperframes` vẫn giữ compatibility và proof trước đó.
Trong mode ffmpeg, không cần VIDEO_EXPORT_HYPERFRAMES/Node/Chrome; cần ffmpeg/ffprobe trên PATH
và Pillow11.3.0 + font Manrope đã có. Unknown renderer báo ValueError, không auto fallback.
Source/ownership/quota/job API/MinIO policy và feature enable flag không thay đổi.

Implementation: Pillow render chữ vào PNG overlay (không nhét user text vào filter/shell),
FFmpeg fixed argv crop/pan theo aspect, H.264 scene clips tuần tự → concat → AAC mix theo
source-locale timing. Music .25/.05 giữ ratio .2. Encode/filter threads1, một process render
mỗi thời điểm, tổng native render timeout180s, ProcessScope termination cũ, cap180s/50MiB cũ.
Không model/provider/cloud hay cached video placeholder. HF backend không bị thay thế.

Linux candidate riêng trên VM được giao: `estagent-video-native:qa-final`, container
`estagent-video-native-final`, không port publish, không volume/env/credentials production.
`deploy/Dockerfile.video-runtime` là candidate độc lập, KHÔNG thay Dockerfile/compose của Deploy:
Python3.13 slim-bookworm, **apt ffmpeg=7:5.1.9-0+deb12u1**, Pillow11.3.0, FastAPI0.138.0.
Đây là QA image tối thiểu; production image cần giữ toàn bộ dependency API hiện có.

Evidence native: `tests/exports/evidence/native-*`. Local app regression4 PASS + config1 PASS;
Linux actual MP4 hai aspect6s H.264/AAC, gain0.200, motion và chữ đã xem, browser playback PASS.
Container cap **1CPU /768MiB /swap cùng768MiB /pids64**, network none lúc render, không OOM.
`native-linux-proof.json` ghi ru_maxrss child/self riêng (KiB); không cộng thành peak tổng.
Kernel không cung cấp memory.peak trong probe này: chỉ claim RSS từng nhóm và hard cgroup bound
đã chạy, không claim worst-case RAM toàn API hoặc full-service throughput đã nghiệm thu.

Deploy NEED: merge code native, đặt VIDEO_EXPORT_RENDERER=ffmpeg, thêm apt pin trên bookworm;
Node/Chrome không cần. Áp lifecycle/MinIO MP4/static build patch đã bàn giao nếu chưa áp dụng.
Giữ feature disabled tới khi integration private MinIO + API smoke hoàn tất; không chặn house-demo.
Không cần root quyết lại framework; mục NEED chọn FFmpeg phía trên là lịch sử trước quyết định này.

Tái lập candidate: build `-f deploy/Dockerfile.video-runtime`, run với
`--cpus=1 --memory=768m --memory-swap=768m --pids-limit=64 --network=none`.
Entrypoint `tests/exports/native_proof.py /output` tạo synthetic input và hai MP4 thật;
không mount data production. Output/scene logs giữ ngoài Git trong candidate và scratch `/tmp`.
Local API checks: `VIDEO_EXPORT_RENDERER=ffmpeg QA_OUTPUT_DIR=<new scratch> uv run --python 3.13
--with pytest --with jsonschema --with-requirements server/assistant/requirements.txt python -m pytest -q tests/exports/test_exports.py tests/exports/test_native_config.py`.
HF vẫn chạy được bằng env cũ; không rerender HF vì không đổi implementation nhánh đó.

Final native candidate evidence: image `sha256:35668661b315348f3ebb539982630c264b0fb0e16c6fae06347b9b0cecc96349`,
exit0/OOM=false; child ru_maxrss177628 KiB, Python61744 KiB. Đây không phải peak RSS tổng app.
Hai file final có SHA256 trùng artifact đã browser phát; `native-linux-artifacts.json` lưu hash.
MP4 local: `/private/tmp/estagent-video-native-linux-final/{portrait,landscape}.mp4`;
VM: `/tmp/estagent-video-native-final-result/{portrait,landscape}.mp4`. Đều6s, 720×1280/1280×720,
H.264/AAC, duck0.200. Container đã exit; không app/edge/volume/credential production bị đổi.
Native code dùng nguồn/dependency hiện có, Pillow11.3.0 và Manrope OFL; Debian FFmpeg5.1.9 GPL
thay runtime HF trong mode mới, không bundle binary/media vào Git. H0 vẫn unknown.
