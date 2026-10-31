# VIDEO-EXPORT — capability prototype

Authority: Tatejo dispatch from Thái, 2026-10-31. Owner feature/video-export;
base 6c50572344930f338b83517c908b88edf05dd8f1. 45 minute timebox.
Paths: server/exports/, tests/exports/, web/export.html/js/css, Creator export entry,
server/tours/api.py additive install hook, this card and VIDEO-EXPORT-HANDOFF.md.
No root/deploy/dependency/storage adapter writes, paid calls, external media, push or merge.

Build owned published checkpoint snapshot → portrait/landscape preview → queued job → private MP4.
Snapshot order, locale, image/audio refs and rights remain immutable. Begin at approved start_scene_id,
then follow the ordered scenes cyclically once, matching the interactive tour opening. Preview discloses silent/partial
recordings; no synthesized voice, generated geometry or adjacency. Default 720p, 24fps.
Implementation contract in this card is additive, not a replacement for tour manifest.

API under /api/tours/exports: GET /sources lists owned publications; GET /preview/{tour_id}?aspect=
portrait|landscape returns scene timings/audio state; POST {tour_id,aspect,request_id};
GET /{job_id}; GET /{job_id}/download (private Range). Missing cookie 401, other owner 404;
idempotent request replay, mismatch409. States queued/rendering/ready/error; stage from real actions.
Single renderer with service file lock, queue bound2, persisted global daily12 and owner daily4 job
allowances; no allowance refund on render failure, restart marks pending jobs interrupted without replay.
Limits prototype: <=20 scenes and <=180s; silent scenes3s, recorded scenes max(3,duration+.3).
No truncating narration to fit limit: oversized source rejects422. Fixed argv and child-group timeout.
Feature default disabled; VIDEO_EXPORT_ENABLED=1 requires explicitly configured HyperFrames CLI.
Local outputs require VIDEO_EXPORT_LOCAL_QA=1; production output requires approved MinIO namespace patch.

Acceptance: synthetic two-scene actual MP4 both ratios, ffprobe codec/audio/duration, real browser,
immutability/private owner/idempotency/restart/error/timeout. Source assets generated at runtime,
outputs outside Git. All baseline checks pass except pre-existing core SKIP; no provider use.
OpenAI: not used. H0 unknown; sources/licenses/evidence/NEED recorded in handoff.
