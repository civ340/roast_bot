---
type: spec
task_slug: ci-frontend-checks
status: approved
created: 2026-11-28
tags: [ci, github-actions, frontend]
test_framework: pytest (repo-root tests/, parses the workflow YAML)
interview_rounds: 0
summary: Add a frontend-checks job to the GitHub Actions CI so every push to master and every PR runs ESLint (0 warnings) and the TypeScript + Vite build.
---

# SPEC — ci-frontend-checks

## Intent
`.github/workflows/ci.yml` only runs `backend-tests`; nothing in CI checks `frontend/`, so a PR
can break lint or the build and still show green. Add a job that runs the same checks
`tests/test_frontend_lint.py` runs locally.

## Scenario
- **S1** Given `.github/workflows/ci.yml`, When it is parsed, Then it has a `frontend-checks`
  job that runs in `frontend/` on `ubuntu-latest` with Node 20, installs with `npm ci`, runs
  `npx eslint . --max-warnings 0` and `npm run build`; the existing `backend-tests` job and the
  triggers (`push` to `master`, `pull_request`) are unchanged.

## Non-Goals
- No branch protection / required-check setup on GitHub (repo setting, not code).
- No frontend unit-test runner (vitest etc.); no change to `frontend/` sources or `backend/`.
- No change to `tests/test_frontend_lint.py`.

## Acceptance Criteria
### AC-001: ci.yml runs frontend lint and build alongside backend tests
Parsing `.github/workflows/ci.yml` yields a `frontend-checks` job with `working-directory:
frontend`, `actions/setup-node` at Node 20, and run steps `npm ci`, `npx eslint . --max-warnings 0`,
`npm run build`; `backend-tests` still runs `pytest -q`; `on` still has `push: {branches: [master]}`
and `pull_request`.

## Verification
| Scenario | Mode | AC |
|---|---|---|
| S1 (workflow shape) | unit (pytest parses YAML) | AC-001 |
| S1 (commands actually pass) | manual: run lint + build locally; GitHub run on the PR | AC-001 |

## Open Questions
none

## Refinement Decisions
- Interview skipped (Step 0): one config file, acceptance obvious from the title, no API/schema/file-format change, reversible by reverting one file. Undo: revert `ci.yml`.
- Node 20 chosen to match `frontend/Dockerfile` (`node:20-alpine`), so CI builds with the same major version as the image. Undo: change one line.
- Lint uses `--max-warnings 0` (stricter than `npm run lint`), matching `tests/test_frontend_lint.py` AC from SPEC-fix-useeffect-deps.
- `tests/test_frontend_lint.py` is left in place; deleting it is out of scope.
- `[intent] none` — no intents defined.
