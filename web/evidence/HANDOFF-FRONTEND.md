# Bàn giao chung EN/VI + motion

Nhận từ: Tatejo (`w6B:p1`), frontend lane `w6D:p1`, theo bổ sung điều phối và `docs/LANE-DISPATCH.md`.
CWD: `/Users/anhoaithai/Documents/AHT/1. PROJECTS/CodexHackathon`.
Commit nền quan sát: `9a1e40f` — `web: record new origin and Vercel integration blocker`.
Không commit/push/stash hay thay Git state. Bản bàn giao là các thay đổi chưa commit trong checkout chung. Sau bàn giao, frontend dừng ghi build/package để Tatejo tích hợp.

## Đã làm

- EN mặc định; sửa bản VI cũ chỉ nói upload ảnh thành cùng luồng ảnh + hội thoại + form + tóm tắt như EN. Dịch đủ nhãn phụ, metadata, title, alt và aria.
- Reproduce trước sửa: landing `en`, workspace tab `vi`, saved preference `vi`. Sửa sync qua storage, pageshow/BFCache và tab visibility; không ghi preference ngược theo vòng lặp và không làm mất form đang nhập.
- Cache: browser từng giữ script i18n cũ dù server trả source mới qua no-store; đã version URL i18n/fonts/styles trong hai HTML và kiểm lại bằng browser.
- Typography: Urbanist subsets thiếu ký tự Việt. Chuyển cả EN/VI sang Manrope variable chính thức (OFL), kiểm đủ 98 ký tự Việt, không sửa binary upstream. Giữ font Urbanist làm reference và thêm giấy phép.
- Motion: hero stagger, scroll reveal, ảnh/card hover, button press, menu/dialog entrance, chuyển trang 160ms. Giữ modifier/hash/native links, keyboard và Back; reduced motion tắt animation cả initial/runtime, không để nội dung ẩn khi JS tắt. Không thêm dependency.

## File list của bundle frontend

- `web/index.html`, `web/experience.html`: language labels/meta và wiring/version assets/motion.
- `web/i18n.js`: nội dung VI + đồng bộ locale.
- `web/styles.css`, `web/assets/fonts.css`: cùng font Manrope EN/VI.
- `web/motion.js`, `web/motion.css`: chuyển động native.
- `web/assets/manrope-variable.ttf`, `web/assets/Manrope-OFL.txt`, `web/assets/Urbanist-OFL.txt`, `web/assets/SOURCES.md`: font/provenance/license.
- `web/build.mjs`, `web/package.json`: motion assets và syntax check đã thêm trước bàn giao. Giữ nguyên phần build `assistant.html/css/js` có sẵn của lane Chatbot.
- `web/README.md`: cách hoạt động, giới hạn và declaration.
- `web/evidence/locale-sync-smoke.js`, `motion-smoke.js`, `intake-smoke.js`: browser scripts (intake chờ URL sau fade).
- `web/evidence/locale-sync-check.log`, `final-motion-check.log`, `final-intake-check.log`, `final-web-gate.log`, `font-coverage.txt`: kết quả cuối.
- Screenshots: `locale-sync-en.png`, `locale-sync-vi.png`, `motion-hero.png`, `motion-sections.png`, `motion-mobile-reduced.png`, `bilingual-home-{en,vi}.png`, `intake-desktop.png`, `intake-mobile-{320,390}.png`.
- `web/evidence/ASSET-AUDIT.md`, `MOTION-RESULTS.md`, file bàn giao này: audit/evidence.

Không sửa `web/assistant.*`, backend, AGENTS, .env hay .env.example. Các thay đổi ngoài danh sách có thể thuộc lane khác; không stage chúng theo báo cáo này.

## Evidence cuối

- `bash scripts/gate.sh web`: lint PASS, 6 unit tests PASS, build PASS; contract SKIP do thiếu `fixtures/tour.schema.json`. Không claim strict xanh hoặc backend e2e.
- `locale-sync-check.log`: toàn bộ text landing đổi ngôn ngữ (ngoại trừ brand/language codes), nội dung tương ứng, title/meta/alt/aria, 3 chu kỳ EN↔VI, cross-tab hai chiều, không mất form input, BFCache pageshow, Back thật, reload, storage unavailable, 320/390/768/1440px không overflow, font tải thật.
- `final-motion-check.log`: animation chạy thật, reduced-motion initial/runtime, button/scroll, chuyển trang/Back/keyboard, modifier/hash links, mobile, no-JS; không browser errors.
- `final-intake-check.log`: EN/VI + chat local/form/draft + upload/preview/remove/invalid + responsive regression PASS sau thay font và locale.
- `font-coverage.txt`: SHA256 font và 98/98 glyph tiếng Việt có mặt. Chỉ browser Chromium local; không claim Safari/Firefox hoặc FPS máy yếu.

## NEED / giới hạn

1. Hero Aigocy vẫn active nhưng quyền dùng production chưa xác minh. Tatejo cần xác nhận quyền hoặc duyệt thay. `ASSET-AUDIT.md` có patch đề xuất dùng `apartment-light.jpg` Pexels đã tải và có license, không mua/generate. Chưa tự thay artwork vì Thái yêu cầu bám reference này.
2. Không nối workspace với `assistant.*` hoặc đổi API contract trong task này. Khi cần nối, cần chốt endpoint + request/response với lane Chatbot trước; frontend hiện giữ local-preview disclosure.
3. Không deploy. Tatejo giữ Git và triển khai từ commit đã nghiệm thu. Contract fixture vẫn thiếu.

## Declaration

Code EN/VI/motion: Codex hỗ trợ viết mới/sửa frontend, native CSS/WAAPI, tham khảo skill framer-motion-animator; không cài Framer Motion. H0 chưa xác nhận, không claim build trong giờ thi. Ảnh apartment: Pexels, ledger tại assets/SOURCES.md. Hero: reference Aigocy do Thái cung cấp, license chưa rõ. Manrope/Urbanist: SIL OFL đã kèm; Manrope active, Urbanist reference. Không gọi AI API hoặc dùng dịch vụ trả phí.

## Bổ sung backlog audio tour — chưa triển khai

Đã đọc `docs/TOUR-AUDIO.md` sau Acceptance card web-04. Yêu cầu trực tiếp: mỗi tour có nhạc nền và lời giới thiệu riêng từng khu, EN/VI có audio/phụ đề đúng ngôn ngữ. Frontend nhận player hai lớp, controls riêng, ducking và đồng bộ room-camera-phụ đề; mở hội thoại phải tạm dừng lời tour, chỉ resume khi người dùng chọn. Không chồng giọng chatbot/tour. Không gọi dịch vụ nhạc/TTS trả phí, không mở code audio trong card EN/VI + motion.

NEED cho card audio kế tiếp: Tatejo chốt schema additive và đơn vị/mốc timing (toàn tour hay từng khu), quyền sở hữu playback và sự kiện chatbot/mic; cấp fixture ít nhất hai khu có narration EN/VI, timing thực và một track nhạc có nguồn/license. Chốt budget/provider nếu cần sinh audio live; nếu chưa có budget chỉ dùng asset được phép và fixture đã cấp.

CONTRACT_CHANGE đề xuất, chưa áp dụng: bổ sung cấu hình nhạc nền và tài nguyên narration/phụ đề theo room/checkpoint + locale, duration/timing và nguồn/credits; giữ tương thích `narration.lines[].room` hiện có. Không tự đặt field API hoặc sửa tour.json. Card kế tiếp phải kiểm audio phát thật, ducking, không chồng giọng, pause/resume/seek/đổi khu nhanh/chuyển locale/lỗi tải; screenshot không đủ chứng minh audio.

## Bổ sung backlog hai view — chưa triển khai

Đã đọc `docs/USER-VIEWS.md` và bản cập nhật `docs/LANE-DISPATCH.md`. Creator: nhập/upload → draft → chỉnh thông tin/lời/nhạc từng khu → preview/duyệt/publish. Viewer: chỉ đọc tour đã duyệt, khám phá/chuyển khu, nhạc + narration và chatbot theo spatial context; không có công cụ sửa/publish. MVP không auth; không suy ra tài khoản hoặc role security mới. Không mở rộng code của card hiện tại.

NEED: integrator chốt hai entry từ landing, route, vòng đời draft/published và dữ liệu/context bàn giao với AI/Deploy. Đề xuất phù hợp frontend tĩnh hiện có: giữ `experience.html` làm entry Creator tương thích, bổ sung `viewer.html?tour=<id>` cho Viewer; đây chỉ là đề xuất chưa triển khai/chốt.

CONTRACT_CHANGE đề xuất: phân biệt dữ liệu draft và snapshot tour đã publish/duyệt; Viewer nhận snapshot được duyệt và context room/checkpoint hiện tại, Q&A/navigation không trở thành sửa metadata. Giữ tương thích API/tour contract hiện có; endpoint, field, revision/timing và hành động publish do integrator chốt cùng audio proposal. Không thêm auth hoặc tự đặt schema bằng test.

STATUS: DONE
CHANGED: frontend bundle/file list ở trên
EVIDENCE: locale-sync-check.log + final-motion-check.log + final-intake-check.log + final-web-gate.log
NEED: quyền hero hoặc duyệt asset thay; fixture contract cho strict gate; chốt audio + hai view/route/draft-published cho card tiếp theo
CONTRACT_CHANGE: audio và hai view proposal ở trên, chưa áp dụng; EN/VI + motion không đổi contract
NOTES: local frontend only; no Git/deploy; build/package ownership trả Tatejo sau bàn giao
