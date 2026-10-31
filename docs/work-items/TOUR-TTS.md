# TOUR-TTS — delegated Creator speech, EN/VI

Owner: Chatbot, feature/tour-tts, base 37962a3d6ab198dfde7e336e9c61d697a47a0a3f (fetched origin/main; contains local main 5498fdc).
Authority: direct task brief from Tatejo within Thái's scope, 2026-10-31. No auth/deploy/spawn. Updated direct authority: two short live TTS calls using .env.local, ≤300 chars each, retries0 timeout30, private output, no global chat key.
Paths: server/narration/, tests/narration/, web/narration-panel.js/css, docs/work-items/TOUR-TTS.md, docs/TOUR-TTS-HANDOFF.md; additive server/tours/models.py/audio.py, fixtures/tour.schema.json/checkpoint-tour fixture; Viewer audio language handling only.
Do not modify Creator html/js, server/tours/api.py, app/static/build/package/deploy/dependencies. Return exact hook patch.

Acceptance: Creator-approved script/hash, scene+revision+locale+voice+request ID → bounded durable job → WAV preview → explicit attach → immutable publish; bilingual generated provenance, missing-track Viewer behavior; real SQLite/MinIO adapter with SDK fixture; local browser playable fixture WAV. Existing audio/AI regression. No live voice-quality claim.
OpenAI: existing configured OPENAI_MODEL_TTS (default gpt-4o-mini-tts), separate backend OPENAI_TTS_API_KEY; deterministic SDK fixtures plus explicitly authorized two EN/VI live samples, retries zero, timeout30. Speech API official reference deprecated, shutdown 2027-01-06; no automatic Realtime migration/fallback.
Sources: official text-to-speech guide and audio/speech/create reference read 2026-10-31. H0 unknown; Codex-assisted new code on existing repo.

Implementation proposal authorized by brief: additive AudioTrack.generation provenance (model/voice/script hash/locale); audio.source openai_generated/mixed; up to 40 unique scene/locale bindings for 20 scenes ×2 locales. Legacy upload source-locale behavior retained. API hooks /api/tours/narration with existing cookie/origin and draft callbacks; no automatic translation or attachment.

Execution evidence: baseline AI strict PASS; implementation targeted17 PASS; full AI+then-narration176 PASS; final AI strict PASS; browser fixture/keyless/real generated-WAV playback PASS. Actual two authorized live calls EN56chars/VI73chars, coral, 4.95s/6.15s, PCM24k16mono. No additional paid calls; no human pronunciation signoff. Exact protected-file NEED patches and config remain in `docs/TOUR-TTS-HANDOFF.md`; production route/Creator/export wiring is not claimed complete.
