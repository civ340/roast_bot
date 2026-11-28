---
type: plan
task_slug: ci-frontend-checks
status: complete
created: 2026-11-28
spec: "[[SPEC-ci-frontend-checks]]"
summary: Add a frontend-checks job (npm ci, eslint --max-warnings 0, npm run build) to the CI workflow.
---

# PLAN — ci-frontend-checks

One phase is enough: the change is one new job in one YAML file.

- [x] **P1** add `frontend-checks` job to `.github/workflows/ci.yml` — scope: `.github/workflows/ci.yml`, `tests/test_ci_workflow.py` · exit: `python -m pytest -q tests/test_ci_workflow.py` · risk: low (CI-only; a wrong step fails CI, never prod) · rollback: `git checkout -- .github/workflows/ci.yml`

## 🚧 Contract Boundaries

### Do not change
- backend/
- frontend/src/
- frontend/package.json
- tests/test_frontend_lint.py

## Decisions
- ADR-001: Node 20 in CI to match `frontend/Dockerfile` (`node:20-alpine`). **Decided by:** agent
- ADR-002: The AC test lives in repo-root `tests/` (next to `test_frontend_lint.py`) and parses the YAML with PyYAML; it asserts the job shape, not that GitHub runs it. **Decided by:** agent
