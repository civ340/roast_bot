---
type: review
task_slug: fix-useeffect-deps
created: 2026-11-27
spec: "[[SPEC-fix-useeffect-deps]]"
plan: "[[PLAN-fix-useeffect-deps]]"
---

# REVIEW — fix-useeffect-deps (round 1, code-reviewer)

Behaviour checked against the original effects: filter change → one page-1 load (batched setFilter+setPage);
page change → load; mount → one fetch (was two, accepted in SPEC); clicking active filter → no-op as before;
auto-refresh → page 1 + current filter every 5 s, no stale closure; manual refresh unchanged.

## Findings
| id | severity | file:line | finding | disposition | authority |
|---|---|---|---|---|---|
| R1 | P3 | frontend/src/pages/Logs.tsx:36-41 | pre-existing: fetches have no cancel/ordering guard; a slow older response can overwrite a newer one; setLoading after unmount | pre-existing | reviewer `pre-existing:` tag; same code before this diff |
| R2 | P3 | repo root | `.gitignore` modified and `.tmp_diff1.txt` untracked, outside PLAN scope | rejected | both present in the session-start git status, not produced by this task; wrapup excludes them from the commit |

## Gate notes
- `npx eslint . --max-warnings 0`: 0 problems; `npm run build`: ok; `pytest tests/test_frontend_lint.py` (ephemeral pytest via uv): 1 passed.
- `hm check` gates exit 127 locally: `pytest` not on PATH, and `cd frontend && …` CI commands do not run without a shell on Windows. Environmental, not a code failure.
