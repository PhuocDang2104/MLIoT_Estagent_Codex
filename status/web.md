# status — web/deploy

- LIVE https://estagent.duckdns.org — source `e0002f440c05a3b3d3a3b06f53108867152c9f1a`, image `ea236835ad8dd33832f9a2acf0e855c7eb290de049cb19993f02b0385d310bbd`. Artifact from clean pushed main, checksum verified; app + MinIO healthy.
- Creator/Viewer two landing entries EN/VI, glass immersive Viewer, Studio durable runtime and private MinIO integrated. No new auth; Studio route retained. Production browser1440/390/320, private PNG/WAV upload/play/pause/reload, Studio save/reload, Viewer fullscreen/panels/drag/keyboard and current-scene POST503 PASS.
- Keyless only; empty OpenAI key. API AI6/min/concurrency1/attempts50h; upload6/min/concurrency1. Storage admission512MiB with1GiB free headroom; dedicated private MinIO hard quota512MiB. App nonroot/read-only/1GiB, MinIO512MiB; no other stack changed.
- Actual multipart WAV5600044bytes/175s,2part ETag, Range/SHA/restart/private checks PASS. Public manifest and8image/thumbnail hashes unchanged. Consistent offline metadata+objects snapshot;10SQLite integrity checks PASS. No production-data restore/deletion or QA publication.
- Evidence: `deploy/evidence/wave3-release/release.json` and `final-production-*.log`, accepted gate/runtime/hash/cutover logs. Real-demo screenshots stay local `/private/tmp/estagent-wave3-viewer-evidence/`.
- Root Tatejo coordinates/reviews/accepts; release lane executes authorized integration/deploy. Main may advance with docs/evidence-only commits after source above; no unaccepted application delta is represented as deployed.
- Remaining next release: OpenAI EN/VI TTS and Video Export. Geometry/reconstruction and physical iOS not verified. Core strict baseline remains SKIP; no strict-all PASS claim. ZIP/dataset public/export rights unconfirmed; no dataset/ZIP published.
- Declaration: Codex-assisted integration/tooling, existing teammate commits/renderer/fonts/assets retained; synthetic QA only, no paid API or new VM/cloud resource. H0 unconfirmed; no claim all source authored during competition.

- Follow-up2c57fbd: glass trong hơn đã deploy/kiểm lại1440/390/320 + hash/TLS; backend acceptance37962a3 giữ nguyên. Không mở rộng TTS/Video.
