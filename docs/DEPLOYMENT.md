# Production — Estagent

Quyết định của Thái ngày 2026-10-31: Tatejo maintain `main` và deploy production; FE trên Vercel, BE từ Git kéo về máy local rồi chuyển lên VM VNPT; database dùng Supabase self-host trên VM.

## Frontend

- Vercel team/project: `meetmate/estagent`.
- Origin mới: `https://github.com/PhuocDang2104/MLIoT_Estagent_Codex.git`; repo cũ giữ ở remote `previous-origin`.
- Chuyển liên kết Vercel sang origin mới đang BLOCKED: API trả HTTP 400 yêu cầu cài GitHub integration. Chủ repo cần cấp quyền tại https://github.com/apps/vercel. Liên kết repo cũ đã gỡ, `project.link = null`; auto-deploy Git tạm ngắt, production hiện có vẫn hoạt động. Vẫn có thể deploy từ local qua CLI.
- Sau khi cấp quyền: `vercel git connect https://github.com/PhuocDang2104/MLIoT_Estagent_Codex.git --yes --scope meetmate` rồi kiểm lại project link.
- Production: https://estagent-weld.vercel.app (đã trả HTTP 200 ở `/` và `/experience.html`).
- Deployment đầu: `https://estagent-exuaiy18m-meetmate.vercel.app`, app source tại `cc8587b` + cấu hình deploy mới.
- Source: `web/`; cấu hình build tại `vercel.json`, output `web/dist/`.
- Hiện là landing page + workspace ảnh chạy trong browser; chưa gọi BE/AI/3D.
- `.vercel` và credentials chỉ lưu local, không commit.

Cập nhật từ checkout sạch trên `main`:

```bash
git pull --ff-only origin main
bash scripts/gate.sh web
vercel link --yes --project estagent --scope meetmate # chỉ lần đầu trên máy mới
vercel deploy --prod --yes --scope meetmate
```

Đối chiếu production URL từ CLI, kiểm trang chủ, CTA → workspace, chọn/xem/xóa ảnh và mobile. Không dùng `--public` (expose source). Gate strict vẫn chưa đạt vì thiếu fixture contract; gate thường chỉ kiểm được FE.

## Backend và database

- Hướng dẫn do Thái chỉ định: tài liệu deploy Minute lên VPC VNPT trong `VinHack/Vòng 2/my_docs/` trên máy local. Đọc tại chỗ, không copy credential vào repo/report.
- SSH vào VM đã được kiểm chứng. VM đang chạy nhiều ứng dụng và hai stack Supabase thuộc project khác; chưa có stack Estagent.
- Tại thời điểm khảo sát còn khoảng 3 GB RAM khả dụng, 72 GB disk. Cần kiểm lại trước khi dựng stack mới.
- Không dùng database/secret/volume của ứng dụng khác cho Estagent.
- BE Estagent chưa có trên `origin/main`; chưa có image/entrypoint/migration để triển khai. Đang chờ repo/nhánh BE hoặc output từ lane AI.
- Khi có BE: fetch về local, kiểm commit + gate, chuyển artifact từ commit đó qua SSH vào release riêng của Estagent, dùng Compose project/volume riêng, kiểm health trước khi đổi route. Giữ release trước để rollback; không chạy `compose down` trên stack dùng chung.
- Cần xác định API HTTPS endpoint trước khi nối FE Vercel; không trỏ browser trực tiếp vào private IP VM.

## Nguồn

Cấu hình deploy viết mới bằng Codex ngày 2026-10-31; không copy source Minute hoặc House VR Tour. Tài liệu Minute chỉ tham khảo hạ tầng. H0 chưa xác nhận, không claim build trong giờ thi. Tham khảo cấu hình: https://vercel.com/docs/project-configuration và https://vercel.com/docs/cli/link.

## Bằng chứng ngày 2026-10-31

- `bash scripts/gate.sh all`: FE lint/build PASS; core, AI, contract SKIP vì chưa có implementation/fixture.
- `bash scripts/gate.sh all --strict`: FAIL do những SKIP trên; chưa đủ điều kiện tuyên bố sản phẩm end-to-end hoàn tất.
- Production `/`, `/experience.html`, `/assets/hero.jpg`: HTTP 200; `/AGENTS.md`: 404.
- Playwright production PASS: CTA, chọn ảnh, xem/xóa/clear, từ chối ảnh lỗi, menu mobile và không tràn chiều ngang 320/390px; không có browser errors.
- Log kèm script thực thi: `web/evidence/production-check.log`; screenshots `web/evidence/prod-*.png`.
- Lần chạy browser đầu timeout vì chọn file trước khi trang tải xong; thêm `waitForLoadState('load')` sau CTA trong test rồi chạy lại PASS, không sửa app.
- BE/DB Estagent chưa triển khai; mới kiểm SSH và tài nguyên VM, không thay đổi các stack hiện có. Chưa có review độc lập khác provider.
