from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNBOOK_PATH = REPO_ROOT / "docs" / "warning-agent-local-autopilot-clean-start-runbook.md"
README_PATH = REPO_ROOT / "README.md"



def test_local_autopilot_clean_start_runbook_covers_required_stable_start_controls() -> None:
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "docs/plan/README.md" in runbook
    assert "docs/plan/active_PLAN.md" in runbook
    assert "docs/plan/active_STATUS.md" in runbook
    assert "docs/plan/active_WORKSET.md" in runbook
    assert "dirty-repo initial-run guard" in runbook
    assert "git status --short" in runbook
    assert "uv run pytest tests/test_autopilot_control_plane.py" in runbook
    assert "/autopilot-run" in runbook
    assert "/autopilot-resume" in runbook
    assert "checkpoint commit" in runbook
    assert "same-session" in runbook
    assert "Failure matrix" in runbook



def test_root_readme_links_the_clean_start_runbook() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert "warning-agent-local-autopilot-clean-start-runbook.md" in readme
