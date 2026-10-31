# Studio + Seoul production release — 2026-10-31

Production: https://estagent.duckdns.org

- Default creation: `/business/create` (AI / Blender Studio).
- Secondary photo editor: `/business/photos`.
- Library: `/viewer.html`, including existing published photo tours, Studio tours,
  ZInD sample and the new furnished `/demos/seoul-apartment`.
- Source deployed: `80f477b36aa9886516fe8f5225af9ca54e132c0d`.
- Image: `sha256:1123f15664ee4979ae6778a293a8616ac2a4c6af0ddcf96e94ad7745c6ccd45a`.

All remote feature heads were ancestors of the integrated main at release.
Concurrent landing, building-preview and playback-control changes were retained.
This file and the evidence commit may be newer than the deployed source SHA.

## Runtime and evidence

`deploy/evidence/studio-seoul/` records release identity, backup, exact preserved
published-row hashes, public browser checks, Linux tests and live provider usage.

- Strict `scripts/gate.sh all --strict`: PASS, no skips.
- Linux candidate: 227 tests passed, actual Blender 3.4.1 GLB export and FFmpeg.
- Deployment guard tests: 26 passed locally.
- Synthetic Studio browser flow: actual Blender/Three.js, clarification, layout
  approval, panorama selection, music controls and immutable publication passed.
- Synthetic provider streaming browser check: summaries grow through real SSE,
  reload preserves the summary, 320px layout passes.
- Private MinIO upload/deduplication, authenticated assets, multipart WAV,
  cross-part Range, restart and no-local-fallback smoke passed.
- Live VM OpenAI checks: Astra High, Terra Low and Sol Low completed streamed
  Responses calls (61 total tokens), plus one 20-character speech check. These
  check provider connectivity, not an additional live full-house reconstruction.
- Public HTTPS browser: landing 3D illustration, default Studio, photo editor,
  library and Seoul sample passed with no page errors or failed responses.
- Seoul: five markers, all eight original panorama images, floorplan, orbit and
  mobile layout passed. First public model load in this check took 9.24 seconds.

Production uses the user's backend-only key. Defaults are Astra High for modeling,
Terra for vision, Sol for text and gpt-4o-mini-tts for speech. Only public reasoning
summaries are streamed. The persistent Studio allowance is 40 provider calls;
existing global admission limits remain, and narration has 20 attempts / 24,000
characters per hour. These are request limits, not a USD billing cap.
The service has 2 GiB / 1.5 CPU limits; private MinIO and FFmpeg remain enabled.

## Preservation and rollback

The previous release was `975d91a130b1fc6adeae5e6fd6e678ad4841abcc` with
`/opt/estagent/runtime/model-975d91a1.env`. Its image remains available. Current
configuration is `/opt/estagent/runtime/studio-80f477b.env`, mode 0600. No secret
values are included in Git or evidence.

Offline backup (24 files, hashes and SQLite integrity verified):
`/opt/estagent/backups/studio-rollout/20261031T084652612107Z-before-studio-80f477b`.
Existing photo and Studio published rows match the backup exactly. The original
ZInD catalog entry remains identical; Seoul uses a separate immutable namespace.
No data restore or object deletion was performed. Other applications, the edge
proxy, storage service and another team's preview were left running.

The first backup attempt failed because SQLite needed journal metadata on a
read-only mount. The previous app was restarted immediately. The successful
retry stopped the single writer, used the SQLite backup API on its dedicated
volume with normal access, verified the complete backup, and switched the app
under `/opt/estagent/runtime/deploy.lock`. The incomplete first backup has no
completion manifest and is not an accepted restore point.

For rollback, acquire that lock, drain and stop the assistant, take a **fresh**
offline backup, and rehearse the old image against a separate copy of current
data. The old graph lacks new modeling/review states: do not blindly downgrade
after new Studio generations have been created. Prefer a forward fix in that
case. After a successful compatibility check, the previous configuration is:

```sh
docker compose --env-file /opt/estagent/runtime/model-975d91a1.env \
  -f /opt/estagent/releases/975d91a130b1fc6adeae5e6fd6e678ad4841abcc/deploy/compose.yaml \
  up -d --no-deps --pull never assistant
```

This previous configuration is keyless and disables new narration/Blender work.
Never restore an older database over newer user work to make a rollback pass.
Temporary candidate and QA servers were stopped; the user's existing local
server on port 5180 was retained.
