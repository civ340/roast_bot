"""AC tests for SPEC-fix-useeffect-deps: frontend lint-clean and build passes."""
import subprocess
from pathlib import Path


FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


def _run(cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, cwd=FRONTEND, capture_output=True, text=True)


def test_ac_001_lint_clean_and_build():
    lint = _run("npx eslint . --max-warnings 0")
    assert lint.returncode == 0, lint.stdout + lint.stderr
    build = _run("npm run build")
    assert build.returncode == 0, build.stdout + build.stderr
