# Seoul English sample and landing preview

Scope: the user requested English-only video, transcript and generated voice for
the Seoul sample, plus the same furnished model on the landing page. ZInD export
restrictions and production generation limits remain unchanged.

Reproduce using `deploy/generate_seoul_voice.py` with the external credential file,
then `deploy/render_seoul_tour.py` with the original prepared catalog and cached
voice directory. The first command admits at most eight provider attempts; cache
receipts prevent repeating successful calls. Do not regenerate existing voice
merely to redeploy. Narration source is `deploy/seoul_narration_en.json`.

The resulting catalog references all twelve original immutable assets plus four
new content-addressed files: H.264/AAC MP4, PCM WAV, UTF-8 TXT and WebVTT. Only
`catalog.json` and `house/exports/` belong in the deployment package. Intermediate
clips and the local font stay outside the published package. Original imagery,
model, capture mapping and source ZIP are unchanged.

The video is 1920x1080 from 2048x1024 equirectangular inputs. Captions use estimated
sentence timing, rather than word alignment. The viewer labels the voice as
AI-generated, provides native playback and downloads, and pauses competing audio.
Landing uses the existing vendored Three.js/Meshopt decoder for the same Seoul GLB.

Deploy a versioned catalog mount and commit-specific image under the existing
deployment lock. Drain writes, back up SQLite/data, preserve the active 24/minute
upload configuration and all provider caps. Previous image/configuration and
catalog remain available for rollback. Final production evidence is recorded
under `deploy/evidence/seoul-media/` after verification.

Completed 2026-10-31: https://estagent.duckdns.org/ displays the Seoul model and
links to `/demos/seoul-apartment`. The sample exposes a 133.56-second 1080p tour,
English transcript, generated voice and selectable captions. Eight TTS requests
completed; rendering/corrections made no additional provider calls. All sixteen
source/export hashes were verified, the full MP4 decoded successfully, and each
chapter midpoint matched its absolute authored camera angle (mean RGB error < 1).

Production application remains `5200bca18ef65f017228609a1c382062510959ba`, which
already incorporated this feature and the concurrent English/sample-input work.
The guarded first cutover detected that newer deployment and stopped before any
mutation. Final cutover changed only its Seoul catalog mount using
`/opt/estagent/runtime/studio-5200bca-seoul-media.env` (0600), pointing to
`/opt/estagent/runtime/seoul-media-140b87a`. The previous environment is
`/opt/estagent/runtime/studio-5200bca.env`; rollback uses that file with the same
5200bca compose release under the deployment lock, after draining and backing up.
No database restoration or image downgrade is needed to remove these exports.

Backup: `/opt/estagent/backups/studio-rollout/20261031T092419469349Z-before-seoul-media-5200bca`.
All 24 backup files verify; eight existing uploaded assets and published tours
were preserved. Upload 24/minute, Studio 40-call and global AI 50/hour caps remain.
ZInD exports still return 404. HTTP checks verify attachment names and both end
byte ranges for all four outputs. Public source matches the deployed release.

Browser acceptance: landing GLB, rotation pause/keyboard, sample CTA, video play
and seek, visibly rendered English captions, voice/video mutual pause, eight
transcript chapters, SHA-matching downloaded TXT, 390px layout without overflow,
and kitchen checkpoint transition to capture 2 of 8. No browser errors observed.
Strict all gate passed before the concurrent merge; its release reports its own
web/AI and affected demo validation. This media-only cutover adds no application
code beyond that already verified release. See `production.json`, `browser.json`,
`validation.json`, `camera-validation.json` and screenshots in the evidence folder.
