---
type: plan
task_slug: fix-useeffect-deps
status: planning
created: 2026-11-27
spec: "[[SPEC-fix-useeffect-deps]]"
summary: Refactor Logs.tsx data-loading effects so react-hooks/exhaustive-deps is satisfied with unchanged behaviour.
---

# PLAN — fix-useeffect-deps

One phase is enough: the change is confined to one component's effects.

- **P1** scope: `frontend/src/pages/Logs.tsx` effects + `load`; exit: `cd frontend && npx eslint . --max-warnings 0 && npm run build`; risk: changed fetch timing (double/missed fetch on filter/page change, stale filter in auto-refresh); rollback: `git checkout -- frontend/src/pages/Logs.tsx`.

## 🚧 Contract Boundaries
### Do not change
- frontend/src/api/client.ts
- frontend/src/types
- backend

## ADRs
- ADR-001: `load` becomes a `useCallback(p, f)` with only stable setters as deps; one `[page, filter, load]` effect does fetching; filter buttons reset page to 1 in the click handler instead of an effect. **Decided by:** agent
- ADR-002: AC test is a pytest test under root `tests/` shelling out to eslint/build, since the frontend has no test runner and backend conftest imports the app. **Decided by:** agent
