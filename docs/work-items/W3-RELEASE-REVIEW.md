# Release review follow-up — 2026-10-31

User: read Claude review, delegate fixes, continue integration and production rollout.
Tatejo owns main, deployment env, packaging and acceptance. Production remains keyless.

- `upload-storage`: `.worktrees/upload-storage`, `feature/upload-storage`.
  Shared disk/headroom admission across image, WAV and Studio uploads; preserve existing data,
  reject full storage before persistence, validate global cross-session behavior/restart/errors.
  Owner: `server/storage.py`, upload API wiring, dedicated tests and handoff. No deployment access.
- `rollback-safety`: `.worktrees/rollback-safety`, `feature/rollback-safety`.
  Read-only preflight against standalone SQLite backup for target `346a0ba`; inspect actual old
  audio contract, refuse incompatible downgrade, document drain/backup/rehearsal. No restore/migration.
- Tatejo: wire both modules into release, enable existing request guards on keyless production,
  set explicit upload storage admission cap 512 MiB and minimum free filesystem space 1 GiB.
  Existing volume measured 9,360,798 bytes; filesystem had 76.68 GB free before rollout.
- Claude finding about missing `scene_id` was made during merge; verify against final source
  before treating it as a defect. Contextual chat now merged at `5498fdc`, 87 AI tests PASS.

Acceptance: preserve published manifest hashes, reject bounded synthetic requests, pass web/AI/schema
checks and browser flows. Strict all still reports baseline core SKIP. Keep provider calls at zero;
do not claim attempt allowance is a billing cap or storage admission is an OS-enforced filesystem quota.
