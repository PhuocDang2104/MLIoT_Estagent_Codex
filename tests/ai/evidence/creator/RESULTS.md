# Studio verification — 2026-10-31

Integration base: `533c3be`. Runtime snapshot for native QA:
`b2fbe49872003712783d6e240455bbb43a8b8429`.

- `scripts/gate.sh web --strict`: PASS (lint, 6 tests, build, both schemas).
- `scripts/gate.sh ai --strict`: PASS (compile, 29 tests, both schemas).
- `scripts/gate.sh all --strict`: FAIL only at the existing missing core lane.
  No checks were removed or strictness lowered.
- `deploy/verify_local.py`: PASS against committed source, private temporary DBs,
  keyless-preview guards, HTTP/body/Origin/cookie checks, restart/integrity and
  11 assistant regression tests. Windows SQLite probe now closes its connection.
- Three Playwright runs: worker absent/spatial review/reload; synthetic worker
  full publish/Viewer/media/Q&A; actual application with no key. All PASS, no
  page errors, no overflow at 390/320px. See JSON logs and PNGs in this folder.
- Full browser test observes actual WAV media play/ended and music gain 0.048
  while narration plays, plus rapid checkpoint switching/pause. WAV is generated
  test silence, not OpenAI voice. Model fixture is a triangle, not a house.

No live provider/Blender/GPU calls, Docker daemon, TLS rollout or paid operations
were tested. The existing tour schema, Creator/Viewer JS, panorama renderer and
production keyless-preview controls remain unchanged. New Studio uses its own
API/storage/package namespace. Root main was pulled to the integration base;
the feature is on its branch, not merged while the global strict gate is red.
