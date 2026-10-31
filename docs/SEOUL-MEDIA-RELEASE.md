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
