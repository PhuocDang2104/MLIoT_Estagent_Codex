# House visitor chatbot — direct Thái request

Request: complete chatbot for current home demo, no auth. Worktree `.worktrees/house-chat`, feature/house-chat, base4ade918 from fetched main. F remains sole production writer. No changes to shared checkout/VM. No spawning.

User confirmed: reuse existing tour API. Existing published Manifest + Chat/TourReply shapes retained; voice/history helpers use the same /api/tours cookie and Origin boundary. Explicit local live QA budget: 4 text questions + 1 STT + 1 short TTS, retries=0, timeout=30 seconds. Production key remains unchanged.

Paths: server/demo_chat/, server/tours/api.py, server/assistant/app.py, server/demos/__init__.py, tests/ai/test_house_chat.py, web/demos/chat-*, web/demos/house.html, web/viewer.js (one-line visitor capability hook), docs/work-items/HOUSE-CHAT.md, docs/HOUSE-CHAT-HANDOFF.md. Existing-file wiring is an isolated proposal for F to integrate, never concurrent shared-checkout edits.

Target: contextual EN/VI Q&A and clarifying navigation, public descriptions only; persisted session history and idempotency; bounded per-call voice input/output; pause narration/autonext on chat. No Realtime connection, Creator edit or login.

OpenAI source: existing pinned SDK and model config, Responses structured outputs; official speech-to-text and structured-outputs guides checked. Reuse existing Speech adapter; deprecated default lifecycle remains documented. No new dependencies. H0 unknown; new Codex-assisted implementation on existing repository.
