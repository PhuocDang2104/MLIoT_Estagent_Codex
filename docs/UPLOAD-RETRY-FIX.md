# Studio upload-limit correction — 2026-10-31

The generic 429 shown during Save came from the app's upload admission guard,
not OpenAI. Live inspection found upload_burst at 6/6 in a 60-second window,
six assets saved in the affected project, no Studio generations and zero Studio
provider calls. The previous retry path resent every file, including those already
saved; these duplicate requests consumed admission slots before backend deduplication.

Deployed source: `e12582f793273b3e0000c8e47d779309b1da433e`.
Image: `sha256:db5a3a361981bace5165ae89e6a985ac4a7470a6baa401e1a93e622bf7383cf3`.
Runtime env: `/opt/estagent/runtime/studio-e12582f.env` (0600).

- Upload allowance is now 24/minute, concurrency one. The same persisted ledger
  and window duration remain; no counters were manually reset.
- Successful files are retained in memory for a retry of the same form submission.
- Upload 429s with rate/concurrency codes and a valid Retry-After up to 120 seconds
  show a countdown, then retry, with at most three attempts per operation.
- Non-upload/AI work is not automatically retried. Global AI 50/hour and Studio
  cumulative 40-call bounds, plus narration bounds, remain unchanged.
- The user's already-open older page can retry Save now using the higher server
  allowance. Newly loaded pages also get progress retention and automatic waits.
  Browser-selected files cannot survive a full page reload; stored server assets do.

Validation: 45 admission tests passed, web strict gate passed, and a real HTTP /
SQLite browser regression saved 12 synthetic panoramas, floorplan and placeholder
music through actual 429s plus an injected transient failure. Manual retry did not
resend the completed captures. No paid provider calls were made for this fix.
Evidence: `tests/ai/evidence/upload-retry/{browser,production}.json`.

Production HTTPS serves the exact new script and reports Studio/Blender ready.
All eight pre-existing Studio asset rows across the current projects match the
offline backup exactly. Published tours and demo catalog were also preserved.
Backup: `/opt/estagent/backups/studio-rollout/20261031T090526249794Z-before-studio-e12582f`.

Rollback is the preceding `ee6da34` image/configuration under the shared deployment
lock with fresh backup and drained writes, following STUDIO-SEOUL-RELEASE.md. The
old configuration restores the six-upload cap and the reported UX bug; prefer a
forward fix. This patch changes no database or published-tour schema. It is new
Codex-assisted code using synthetic regression data; H0 remains unconfirmed.
