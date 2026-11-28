---
type: review
task_slug: ci-frontend-checks
created: 2026-11-28
spec: "[[SPEC-ci-frontend-checks]]"
plan: "[[PLAN-ci-frontend-checks]]"
rounds: 1
---

# REVIEW — ci-frontend-checks

Reviewer: `code-reviewer` (sonnet, read-only), one round, given SPEC + machine.yaml + PLAN + diff + tests together.

## Findings
| id | severity | file:line | finding | disposition | authority |
|---|---|---|---|---|---|
| R1-01 | P2 | tests/test_ci_workflow.py:4 | Test imports PyYAML, which no requirements file declares | rejected | PLAN `Do not change: backend/` (the only requirements files live there); same pattern as `tests/test_frontend_lint.py`, root `tests/` has no requirements file. Gate runs pass `--with pyyaml`. |
| R1-02 | P3 | tests/test_ci_workflow.py:29 | Test does not pin setup-node `cache` keys or checkout order | rejected | SPEC AC-001 does not require them; nit |
| R1-03 | P3 | .github/workflows/ci.yml:35 | `node-version: 20` floats to latest 20.x | rejected | ADR-001 (match Dockerfile `node:20-alpine`, which floats the same); reviewer: "no action" |

Reviewer also noted (not a defect of this diff): root `tests/` is never run by CI (CI runs `pytest -q` in `backend/`) — pre-existing, same as `test_frontend_lint.py`.

## Gate notes
- `hm check` gates read CI commands from `ci.yml` and run them locally without a shell. On Windows `npx` is a `.cmd` shim, so `npx eslint . --max-warnings 0` exits 127 (WinError 2) — environmental, same as recorded in REVIEW-fix-useeffect-deps-2026-11-27. The same check passes via `mechanical_checks` (`cmd /c "cd frontend && npm run lint"`, `npx tsc -b`: exit 0) and directly (`npx eslint . --max-warnings 0`: 0 problems; `npm run build`: ok).
- `pytest` is not on PATH on this machine; gate runs use `uv run ... --with pytest --with pyyaml`.
- RED: `hm check --red` exit 0 against master's `ci.yml` (AC-001 failed: "CI has no frontend-checks job"); GREEN: 1 passed.
