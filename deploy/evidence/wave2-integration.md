# Wave 2 integration verification

Sources: audio `f095ad1`, guards `0decde3`, teammate Studio `b504dfe`; all merged with history preserved.

- Shared guards now installed in app and included in release/Docker allowlists; Studio admission paths included.
- Web lint/test/build and both manifest schemas PASS. Strict all still fails only baseline missing core SKIP.
- AI suite after wiring: 80 tests PASS (uv pinned requirements).
- Recorded WAV local browser/upload/reload/publish/playback/ducking and server restart PASS; synthetic tones only.
- Studio actual keyless browser/save/reload PASS.
- Studio graph/spatial review/SSE/reload/waiting-worker browser PASS with fixture provider.
- Studio full publish/Viewer/Q&A/media/320px browser PASS with synthetic provider, triangle geometry worker and silence.
- Native deploy preflight/HTTP/origin/body/static/SQLite restart PASS from wiring commit.
- Existing user edit to root `.env.example` is preserved separately; release source uses committed examples only.

Evidence: `wave2-audio.log`, `wave2-studio/`. No provider live calls, production keys or real reconstructed geometry were used.

Before live Studio: uploaded images currently retain source EXIF; strip metadata before enabling publish with real data. Studio admission limits count enqueue/review attempts, not provider calls or worker lifetime. Realtime limits only SDP setup, not stream duration. Keep release keyless. H0 unknown; no build-during-competition claim.
