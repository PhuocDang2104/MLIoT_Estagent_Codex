# DEMO-VIEWER: demo UX fixes
Lane: web
Slug: demo-ux
Network: no

## Goal
P0: all ordinary photos and cylindrical panoramas use immersive viewport on desktop/mobile; clamp camera including horizontal/vertical field of view so no uncaptured black region for drag/arrows/wheel/resize. Keep full360 seamless. Hide Ask AI when session.configured false and hide empty audio panel; show prominent Listen button when current narration exists; preserve playback lifecycle. P1: present opening scene first in local viewer ordering without mutating published records, consolidate disclosure into compact expandable source detail. P2: content language truthful, chat submitted bubbles/history/suggested questions when configured, clean localized errors. Do not claim automatic translation. Preserve existing controls and glass style.

## Paths
web/viewer.js, web/viewer.html, web/panorama.js, web/tour.css (viewer selectors only), web/tests/viewer*.test.js, tests/demo-ux/viewer*
Own this task card/report only in addition. Other files NEED root. CSS separate ownership selectors; root integrates.

## Context
Base d73ba6a origin/main. User explicitly requests parallel lane fixes; original audit base5498fdc/prod346a0ba is stale. Read current source, AGENTS, CONTRACTS, CODEX-OPENAI; backend also BACKEND-HANDOFF/server AGENTS. No .codegraph. No user assets/secrets/production DB copied. Native subagent assigned this worktree; no further agents.

## Acceptance
UV_OFFLINE=1 bash scripts/gate.sh web --strict; targeted behavioral regressions and browser evidence for UI. Synthetic fixture/local data only; never production writes. Parent independently validates integration. Baseline parent ran gate in this worktree (result supplied in brief). 45-minute timebox.

## OpenAI
Fixture mode only, USD0, zero live model calls or new dependencies/config. Existing application provider unchanged.

## Declaration
Adapt repo source d73ba6a, Codex-assisted changes; H0 unverified, no claim all source built in contest. No external assets.

## Handback
Commit only own Paths on this branch (authorized); no push/merge/deploy. Return SHA, exact behavior, gate/browser evidence, remaining NEED/CONTRACT_CHANGE. Preserve concurrent work.
