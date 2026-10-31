# Studio + Seoul production release — 2026-10-31

Production: https://estagent.duckdns.org

- Default creation: `/business/create` (AI / Blender Studio).
- Secondary photo editor: `/business/photos`.
- Library: `/viewer.html`, including existing published photo tours, Studio tours,
  ZInD sample and the new furnished `/demos/seoul-apartment`.
- Source deployed: `ee6da346abafeff28d71a4bb5b329cd4e07c2491`.
- Image: `sha256:fe6c4d9b711451542e53424a91e8bb039b42f39c878c1b662cec25c6e864a89a`.

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
- Public HTTPS browser: landing actual demo dollhouse, default Studio, photo editor,
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

The initial Studio backend release was `80f477b`. A final frontend rollout at
`ee6da34` includes teammate correction `c73c636`: the homepage previews the actual
ZInD dollhouse. Backend, Blender, API configuration and Seoul assets are identical
to the qualified `80f477b` release. Web strict gate and public entry/library/
landing browser checks passed again. All remote branch heads at build time are
ancestors of `ee6da34`. The shared deployment lock is released.

Current configuration: `/opt/estagent/runtime/studio-ee6da34.env`, mode 0600.
Immediate previous configuration: `/opt/estagent/runtime/studio-80f477b.env`.
No secret values are included in Git or evidence.

Two complete offline backups (24 files each, hashes and SQLite integrity checked):

- `/opt/estagent/backups/studio-rollout/20261031T084652612107Z-before-studio-80f477b`
- `/opt/estagent/backups/studio-rollout/20261031T085135975582Z-before-studio-ee6da34`

Existing published rows match the first backup exactly. Both public demo catalog
and published-tour list match the second baseline exactly. The ZInD catalog was
preserved; Seoul uses a separate immutable namespace. No restore or object deletion
was performed. Other apps, edge proxy, storage and another team's preview remain.

The first backup attempt failed because SQLite needed journal metadata on a
read-only mount. The previous app was restarted immediately. The successful
retry stopped the writer, used SQLite's backup API with normal access to its
dedicated volume, verified the complete backup, and switched under
`/opt/estagent/runtime/deploy.lock`. The incomplete first attempt has no completion
manifest and is not an accepted restore point.

To roll back the final frontend update, acquire the shared lock, drain/stop the
assistant, take a fresh offline backup, and use the preceding runtime (identical
backend and schema) against the same data volume:

```sh
docker compose --env-file /opt/estagent/runtime/studio-80f477b.env \
  -f /opt/estagent/releases/80f477b36aa9886516fe8f5225af9ca54e132c0d/deploy/compose.yaml \
  up -d --no-deps --pull never assistant
```

The older `975d91a` / `model-975d91a1.env` release is still retained, but it is
keyless and lacks the new modeling/review graph states. Do not downgrade to that
release after new Studio work without rehearsing against a separate current-data
copy. Prefer a forward fix. Never overwrite newer work with an older database.

Temporary candidate/QA servers were stopped. The existing local server on port
5180 remains running. Realtime voice and transcription were not re-tested in this
rollout; the live checks listed above cover Responses and speech generation.
