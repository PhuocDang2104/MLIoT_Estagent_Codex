# Contextual Creator / Viewer chat — handoff

Date: 2026-10-31. Parent task: continue the agent flow/chatbot for people creating tours
and people viewing homes while integrating teammate code. Base `0c04857`, branch
`feature/chat-flow`, worktree `.worktrees/chat-flow`. Owner paths: `server/tours/api.py`,
`models.py`, `web/creator.js`, `viewer.js`, `tests/ai/test_tour_chat_context.py`, this file.
No changes to Studio's independent generation/chat contract, dependencies, deployment or main.

## Result

- Creator can select **Ask about this scene** on an existing scene card. Clicking the selected
  button again returns to whole-tour context. The submitted `scene_id` is explicit; it does
  not change the opening scene, projection, order or saved draft. Selecting another draft
  clears the context. Retry identity includes selected scene so different targets cannot
  silently reuse one request ID.
- Viewer submits the currently displayed scene with each question. The backend validates
  membership before calling the interpreter/provider. Cross-tour, unknown or malformed
  scene IDs fail 422. Omitting the field remains valid and means whole-tour context;
  the assistant is instructed to clarify ambiguous room references.
- Model/interpreter input adds `scene_id`, `current_scene` and `history`, alongside existing
  `mode`, `tour`, `text`, `locale`. This is context for text-only chat; no image analysis
  or measurements are claimed. The current saved/published tour takes precedence over
  previous conversational descriptions.
- Creator context reads only the authorized draft's successful turns, plus initial text
  while it fits in the excerpt. Viewer context is bound to the cookie session **and**
  immutable published snapshot. It never reads the originating Creator's private brief/turns.
- The excerpt has at most six successful question/answer pairs (12 messages), each text
  truncated to 1000 characters. It contains role/text only, never previous complete manifests,
  attachment bytes or cookies. This limits model context; it does **not** delete stored history.
- Viewer successful turns use a separate `viewer:<hashed-owner>:<snapshot-id>` namespace
  in the existing `turns` table. No table/column/schema migration or record rewrite.
  This history survives process restart with the dedicated tour database.
- Viewer idempotency now returns a prior successful answer for the same session/snapshot/
  request ID and identical body. Reusing that ID with changed text/scene returns 409.
  Creator replay normalizes pre-extension stored requests missing `scene_id`, so old
  cached requests still match the new default null field.
- Model changes/order are still rejected for Viewer; navigation targets must already exist.
  Rejected model proposals never enter history. Creator edits retain ID validation, revision
  checks after the model returns, and clear saved review before another publish.

## OpenAI

Mode: **fixture**, USD 0, zero live calls. Existing model config `OPENAI_MODEL_TEXT`
(existing default `gpt-6.1-sol`), Responses structured output, 30s timeout, retries 0,
1200 output tokens and `store=false` remain unchanged. No tool/provider fallback or
key access. Live use, if separately authorized by the integrator, sends only this
session/tour's bounded text context to existing allowed host `api.openai.com`.
Conversation context is application-managed; no Conversations API or response ID state
is introduced. Official reference checked:
https://developers.openai.com/api/docs/guides/conversation-state.

No-key production continues returning explicit 503 for chat; this change is not live
model-quality verification, paid-call authorization, a token/dollar cap or an auth system.
Sequential replay is supported; concurrent identical submissions may still make more than
one provider call before a successful result is stored. No exactly-once billing claim.

## Evidence

Run from this worktree, with pinned dependencies already available:

```bash
uv run --quiet --python 3.13 --with pytest --with jsonschema \
  --with-requirements server/assistant/requirements.txt python -m pytest tests/ai -q
bash scripts/gate.sh all --strict
node --check web/creator.js
node --check web/viewer.js
python3 scripts/check_commit_attribution.py --all
git diff --check
```

- **87 tests PASS**, including seven new HTTP/SQLite behavior tests. New checks cover
  current scene, follow-up memory, owner/snapshot isolation, restart persistence,
  bounded context, invalid IDs before provider invocation, read-only snapshots,
  review invalidation and replay of old stored request bodies without the new field.
- Strict gate: web lint/test/build, AI compile/pytest, checkpoint + Studio fixtures PASS.
  Exit 1 solely for the known **core SKIP** (reconstruction pipeline absent). Do not
  interpret this handoff as a green global strict gate.
- Actual Chromium → HTTP → SQLite → injected fixture interpreter PASS:
  create/upload two synthetic PNGs → select first scene/chat → select second/follow-up →
  explicit review/publish → Viewer next scene → two questions. Assertions inspect
  actual POST bodies and responses to verify Creator and Viewer active scene and
  isolated history, zero browser page errors and no 390px overflow. No route/network mocks.
- Temporary reproducible runner: `/private/tmp/estagent-chat-context-browser.py`.
  Run using the same uv environment above and this worktree cwd. It starts an isolated
  loopback app/database, launches a uniquely named playwright-cli browser, and closes
  server/browser afterward. It does not load env files or use production data.
- Browser result: `/private/tmp/estagent-chat-context-evidence/browser.log`:
  `pass=true`, `creatorSceneAndHistory=true`, `viewerCurrentSceneAndHistory=true`,
  `historyModeIsolation=true`, `mobile390=true`, `errors=[]`.
  Screenshots inspected: same directory `creator.png`, `viewer.png`. These are local,
  synthetic QA artifacts; integrator may retain them in release evidence if useful.
- Syntax, attribution and whitespace checks PASS. No Claude attribution trailers.

## Integration NEED / declaration

NEED: integrator update `docs/CONTRACTS.md` §7 Chat body with optional
`scene_id:null|existing scene ID` and Viewer successful history/idempotency semantics;
no Manifest/fixture schema change. This lane does not own that root contract document.

NEED: append the following declaration to `docs/DECLARATION.md` when integrating:
context/history validation, Creator scene selector and Viewer current-scene submission
were newly implemented with Codex assistance on 2026-10-31 using the existing tour API/UI,
Python stdlib SQLite and pinned FastAPI/Pydantic stack. No new dependencies, reference-repo
copy, external assets or paid API calls. HTTP/UI tests use generated color PNGs and explicit
interpreter fixtures, not real property/vision/model output. H0 is unconfirmed; do not claim
these changes were written during competition hours.

Tatejo owns review, merge, push and production rollout. Keep preview keyless and preserve
the existing volume. No migration, environment changes or data cleanup are required here.
