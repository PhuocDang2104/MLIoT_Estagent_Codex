# W2-API-GUARDS — bounded public API before live keys

Owner: Chatbot pane `w6E:p1`, branch `feature/live-api-guards`, `.worktrees/live-api-guards`.
User authorized feature completion; MVP remains no auth. This card does NOT authorize enabling real keys or paid smoke.

## Goal and scope

Build and test reusable application middleware to limit public AI requests/concurrency and a persistent
request-attempt allowance. It must be ready for integrator wiring into `create_app` without changing tour/audio code.
Write only `server/limits.py`, `tests/ai/test_api_limits.py`, `docs/API-GUARDS-HANDOFF.md`.
Root app/config/dependency wiring belongs to integrator: return NEED with exact small patch, do not edit it.
Audio lane owns server/tours and schema; do not touch them. No new dependency needed.

## Contract / boundaries

- Provide `install_limits(app, env)` and explicit opt-in config; document secure production defaults proposed,
  distinguish mandatory live configuration versus compatibility diagnostics. Missing/invalid required configured values fail clearly.
- Bound global expensive endpoint requests and in-flight work for `/api/assistant/turn`, `/api/assistant/voice`,
  `/api/tours/drafts/{id}/chat`, `/api/tours/published/{id}/chat`; protect public upload separately if feasible within card.
- Do not trust arbitrary X-Forwarded-For/X-Real-IP. With proxy setup unconfigured, use conservative global limits;
  do not claim per-user identity from a cookie or container IP. No auth/login introduced.
- Persist window/request-attempt allowance on dedicated SQLite (not changing assistant/tour checkpoint schemas),
  restart does not reset allowance unexpectedly. Tests inject clock/storage for deterministic boundary checks.
- No API key, cookie/session token, message/body or arbitrary client URL in ledger/log. Atomic reservation and
  concurrency release on normal/error/cancel; avoid holding DB write transaction over upstream network.
- 429 structured error + Retry-After when exhausted; no fake model response. Compatible with existing error handlers.
- Limits count request attempts, NOT billed tokens/USD. Do not label an estimated counter a guaranteed money cap.
  Realtime SDP setup cap does not bound stream duration; explicitly identify voice billing limits still needed before live voice.
- No enabling env/key, keyless switch or production changes. All tests fixture/no network, no paid calls.

## Acceptance / handoff

Test burst rejection, concurrent max, persisted allowance across app recreation, expiry/reset, invalid config,
exception/cancel release and existing assistant success/error semantics. Use actual FastAPI requests + temp SQLite.
Run existing tests/ai and new tests; no weakening baseline/core gates. Document exact root app/compose/env patch
needed, safe rollout/rollback and any unresolved live voice limit. Commit branch only; no main push/merge/spawn.
Timebox45m/two approaches before PARTIAL with evidence. Handback docs/API-GUARDS-HANDOFF.md.
