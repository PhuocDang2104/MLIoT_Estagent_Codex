# W2-AUDIO handoff — 2026-10-31

## Kết luận và ownership

**Audio acceptance PASS trên local; toàn bộ strict gate vẫn FAIL vì core SKIP baseline.**
Không có runtime blocker mới được reproduce trong phạm vi audio. Chưa deploy/merge/push.

- Nhận từ: Tatejo; card authority: `docs/work-items/W2-AUDIO.md`.
- Cwd duy nhất: `/Users/anhoaithai/Documents/AHT/1. PROJECTS/CodexHackathon/.worktrees/tour-audio`.
- Branch: `feature/tour-audio`.
- Base: `a28e43177533eee4279d97f21c1e408128e5bff6`.
- Implementation + tests + evidence: **`b7944b0b5a0be64302df38380151ce0f83e65a1d`**.
- File này nằm trong commit handoff tiếp theo; lấy SHA cuối bằng `git rev-parse feature/tour-audio`.
- Sau commit handoff, owner dừng ghi để Tatejo review/merge. Không sửa main/product-sync,
  root app/build/package/dependency, `server/limits.py`; không spawn hay gọi provider.

## Đã làm

- `server/tours/audio.py`: kiểm bytes PCM WAV thật, normalize, lưu immutable blob và metadata
  theo owner, private/public read có HTTP Range, gắn/gỡ theo revision và kiểm refs lúc publish.
- `server/tours/api.py`, `models.py`: additive upload/attachment/public routes, metadata audio,
  source-locale bindings, availability trung thực; review bị reset khi đổi audio. Snapshot đã
  publish giữ nguyên refs/bytes sau sửa draft và restart server.
- `web/creator.html`, `creator.js`: upload nhạc hoặc bản thu từng điểm, khai nguồn/quyền,
  transcript tùy chọn, nghe thử/gỡ, reload từ server, yêu cầu review lại trước publish.
- `web/viewer.html`, `viewer.js`, `tour.css`: hai HTMLMediaElement thật, một nguồn lời tại
  một thời điểm; music duck xuống 20% gain khi lời đang phát và không mute, khôi phục khi
  pause/end/mute. Gain/mute độc lập, pause/resume giữ clocks, seek lời, rapid next/previous,
  chat open/focus dừng và close không tự resume; locale/missing/load-error được nói rõ.
- Controller nằm trong `viewer.js` hiện đã được serve/build/lint, không cần đổi root allowlist
  hoặc build script. Visual tour vẫn hoạt động khi không có hoặc lỗi audio.
- `fixtures/tour.schema.json`, `fixtures/checkpoint-tour/tour.json`, `docs/CONTRACTS.md §8`:
  schema và metadata fixture cập nhật cùng nhau; không kèm binary WAV hay URL ngoài.
- Tests/evidence ở `tests/ai/test_tour_audio.py`, `tests/audio/`; nguồn ở `docs/DECLARATION.md §8`.

## Validation đã chạy

Từ cwd trên, dùng dependency/runtime hiện có; các lệnh tái lập:

```bash
uv run --quiet --python 3.13 --with pytest --with jsonschema --with-requirements server/assistant/requirements.txt python -m pytest -q tests/ai
uv run --quiet --python 3.13 --with pytest --with jsonschema --with-requirements server/assistant/requirements.txt python tests/audio/run_browser.py
bash scripts/gate.sh all --strict
node --check web/creator.js
node --check web/viewer.js
python3 scripts/check_commit_attribution.py --all
git diff --check
```

- **30 API tests PASS**: gồm 20 baseline, WAV thật/invalid/truncated/encoding/rate/channel,
  20 MiB và 180 giây, metadata stripping, owner/path boundaries, revision/review, locale,
  immutable snapshot, missing blob, restart, schema equality/legacy compatibility.
  Evidence: `tests/audio/evidence/api-tests.log:1`.
- **Chromium + production application local PASS**, không interpreter/provider fixture:
  Creator upload 3 WAV → reload → private preview phát được → review → publish → Viewer.
  Browser decode durations lời 8s/4s, nhạc 30s; clocks tăng thật; gain .25→.05 khi lời,
  đổi gain .4→.08; mute độc lập, pause/resume, seek/end restore, rapid scene change,
  chat cancellation/no auto-resume, locale mismatch và thiếu lời đều được assert.
  Evidence: `tests/audio/evidence/browser.log:1` (27 media events, zero page errors).
- **Restart server thật PASS**: public audio vẫn phát và truy cập được trong context mới
  không owner cookie; gỡ audio draft không đổi published snapshot.
  Evidence: `tests/audio/evidence/browser.log:3`.
- Load error probe chủ động abort **một WAV request** để kiểm thông báo lỗi và visual navigation;
  không thay API/media playback bằng mock. Các request ngoài local origin bị chặn trong harness.
- Screenshot đã xem: `tests/audio/evidence/viewer-recorded-audio.png` và
  `tests/audio/evidence/audio-controls-mobile.png`; không overflow ở 320/390px.
- Strict gate: web lint/test/build PASS, AI compile/tests PASS, contract PASS;
  **exit 1 vì core SKIP (chưa có code)**. Không hạ strict hoặc tạo test giả cho core.
  Evidence: `tests/audio/evidence/gate-strict.log:7` và `:15`.
- Syntax, diff whitespace và attribution check PASS; không có attribution Claude trong commit.
- Hai lần browser đầu đọc kết quả trước event `details.toggle`/media rejection nên đỏ;
  sửa harness chờ trạng thái DOM/media thực với timeout, không sửa app để ép test xanh.
  Lần cuối browser + restart đều PASS; log lưu kết quả lần cuối.

Harness cần `playwright-cli` và Chromium đã cài, tạo server/DB/media tạm trong `tests/audio/`,
không đọc key, không tải asset và đóng browser/server sau chạy. Các dependency là bản đã có;
`uv` có thể cần quyền cache trong môi trường sandbox. Không commit WAV/PNG input/DB/env.

Để review thủ công: `bash scripts/dev.sh`, mở `http://127.0.0.1:5180/creator.html`;
Viewer qua preview hoặc link publish do UI sinh. Test dùng cổng loopback động và snapshot
trong DB tạm; URL đó không còn tồn tại sau harness. Không có server/deploy mới được giữ chạy.

## Contract và compatibility

- Giữ `checkpoint-tour-v1`; shape cũ `audio={status: unavailable, source: none,
  narration: null, music: null}` còn valid. Metadata fixture mới chỉ minh họa shape;
  refs placeholder không phải endpoint audio sống.
- Additive `POST /api/tours/audio-assets`, owner-only `GET /api/tours/audio-assets/{id}`,
  `PUT /api/tours/drafts/{id}/audio`, public `GET /api/tours/published/{id}/audio/{asset_id}`.
  Upload raw WAV + percent-encoded JSON `X-Audio-Metadata`; không nhận URL/path/base64.
- Narration gắn scene + ngôn ngữ gốc tour. Đổi locale không relabel/translate bản thu cũ;
  Creator có nút gỡ nhóm ngôn ngữ cũ trước khi gắn mới. Music optional; ready nghĩa đủ
  narration cho mọi scene theo source locale, partial có refs nhưng còn thiếu, unavailable rỗng.
- PUT audio thay toàn bộ refs, tăng revision, reset review. Publish kiểm owner/metadata/blob
  và tạo URL theo snapshot. Chỉ asset thuộc snapshot mới được public read.
- Bảng SQLite `audio_assets` được tạo additive/lazy trong tour DB local; không sửa bảng cũ,
  không chạy migration production. Blob được giữ immutable; không có delete/garbage collection.

## Giới hạn, nguồn và mock/live

- MVP **WAV PCM format 1, 16-bit little endian, mono/stereo**; sample rates 8000, 11025,
  16000, 22050, 24000, 32000, 44100, 48000 Hz. Mỗi track tối đa 20 MiB **và** 180 giây;
  tối đa 100 asset/session. Không MP3/AAC/float WAV/24-bit/WAVE_FORMAT_EXTENSIBLE, transcoding,
  microphone recording, transcription, TTS hoặc AI voice. UI/error công khai giới hạn.
- Live ở đây chỉ là local upload/storage/WAV decode/HTMLMediaElement playback thật.
  Dữ liệu kiểm thử là sine tone 220/440/660 Hz và ảnh màu do harness sinh, không phải
  giọng người/nhạc có bản quyền/ảnh nhà; API fixtures dùng constant PCM samples.
  Chưa nghe/đánh giá chất lượng bản thu người thật; chưa test Safari/iOS hay thiết bị vật lý.
- Không provider/paid calls; backend AI vẫn theo cấu hình hiện có, thiếu key báo lỗi trung thực.
  Device speech chỉ là fallback gắn nhãn, không chứng minh recorded/OpenAI narration và
  không được kiểm audible quality trong task này. Không claim production/3D/full-360.
- Code mới Codex-assisted trên baseline repo; không copy reference repo, thêm dependency hay
  tải asset. Dùng Python stdlib wave (PSF license) và dependencies đã có. Source/rights input
  là tự khai của uploader, không xác minh độc lập. Không nhạc/giọng/demo private được bundle.
- H0 chưa xác nhận: không claim code viết trong giờ thi. Existing hero asset audit/license
  vẫn chưa được lane này giải quyết; demo cơ chế không chứng minh hiệu quả shortlist thuê nhà.

## NEED — root README patch để integrator áp dụng

README.md:38–39 còn nói chưa hỗ trợ audio; ngoài Paths được giao nên không sửa trực tiếp.
Không cần root build/package/app/dependency patch. Patch copy đề xuất:

```diff
--- a/README.md
+++ b/README.md
@@
-- Recorded narration and licensed background music are unavailable. Viewer controls expose that state and offer
-  optional **device speech fallback**, only for the tour's source language. This is not OpenAI narration.
+- Creator can upload their authorized recorded narration and background music as PCM 16-bit WAV
+  (mono/stereo, supported 8–48 kHz rates, ≤20 MiB and ≤180 seconds per track). Sources and rights
+  are uploader declarations. Viewer shows missing audio honestly, with an optional labelled
+  **device speech fallback** for the source language; this is not OpenAI narration.
+  See [audio handoff](docs/AUDIO-HANDOFF.md) for exact formats, evidence and limitations.
```

Tatejo giữ review/main/deploy; cần review và áp dụng README patch khi merge.
Core strict SKIP còn baseline; không có yêu cầu mở feature hoặc chạy paid service mới.
