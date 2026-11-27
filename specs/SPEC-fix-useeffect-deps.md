---
type: spec
task_slug: fix-useeffect-deps
status: approved
created: 2026-11-27
tags: [frontend, react, lint]
test_framework: eslint + tsc (frontend has no unit-test runner)
interview_rounds: 0
summary: Remove the 3 react-hooks/exhaustive-deps warnings in frontend/src/pages/Logs.tsx without changing observable behaviour.
---

# SPEC — fix-useeffect-deps

## Intent
`npx eslint .` in `frontend/` reports 3 `react-hooks/exhaustive-deps` warnings, all in
`src/pages/Logs.tsx` (lines 43, 44, 50). Clear them so lint is clean, keeping page behaviour.

## Scenario
- **S1** Given the Logs page, When `npx eslint .` and `npm run build` run in `frontend/`,
  Then eslint reports 0 problems and the build succeeds; and filter change → reload page 1,
  page change → reload that page, auto-refresh → reload page 1 with current filter every 5 s,
  manual refresh → reload current page — all still hold.

## Acceptance Criteria
### AC-001: Logs.tsx lint-clean and build passes
`npx eslint .` exits 0 with "0 problems" output and `npm run build` exits 0.

## Verification
| Scenario | Mode | AC |
|---|---|---|
| S1 (lint/build) | integration (CLI) | AC-001 |
| S1 (behaviour) | manual code review of effect triggers | AC-001 |

## Open Questions
none

## Refinement Decisions
- Interview skipped (Step 0): single file, obvious acceptance, no API/schema change, reversible in minutes.
- Fix approach: make `load` a stable `useCallback` taking explicit args, and drive fetching from a
  single `[page, filter]` effect; filter change resets page via the filter setter path. Side effect:
  removes the existing duplicate fetch on mount / filter change — accepted as not user-visible. Undo: revert one file.
- Verification by eslint + tsc because the frontend has no test runner; adding vitest is out of scope.
- `[intent] none` — no intents defined.
