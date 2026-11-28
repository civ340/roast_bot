"""AC tests for SPEC-ci-frontend-checks: CI runs frontend lint + build beside backend tests."""
from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "ci.yml"


def _load():
    with WORKFLOW.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _runs(job):
    return [s["run"] for s in job["steps"] if "run" in s]


def test_ac_001_frontend_checks_job():
    wf = _load()
    jobs = wf["jobs"]

    # PyYAML (YAML 1.1) parses the bare key `on` as boolean True.
    triggers = wf.get("on", wf.get(True))
    assert triggers["push"] == {"branches": ["master"]}
    assert "pull_request" in triggers

    assert "frontend-checks" in jobs, "CI has no frontend-checks job"
    fe = jobs["frontend-checks"]
    assert fe["runs-on"] == "ubuntu-latest"
    assert fe["defaults"]["run"]["working-directory"] == "frontend"

    node = [s for s in fe["steps"] if str(s.get("uses", "")).startswith("actions/setup-node")]
    assert len(node) == 1, "frontend-checks must set up Node exactly once"
    assert str(node[0]["with"]["node-version"]) == "20"

    assert _runs(fe) == ["npm ci", "npx eslint . --max-warnings 0", "npm run build"]

    assert "pytest -q" in _runs(jobs["backend-tests"])
