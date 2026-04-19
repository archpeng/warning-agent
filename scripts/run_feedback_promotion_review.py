from __future__ import annotations

import json
from pathlib import Path

from app.feedback.compare import DEFAULT_COMPARE_SUMMARY_PATH
from app.feedback.promotion import run_feedback_promotion_review


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    decision, report = run_feedback_promotion_review(
        compare_summary_path=repo_root / DEFAULT_COMPARE_SUMMARY_PATH,
        repo_root=repo_root,
    )
    print(json.dumps(decision, indent=2, ensure_ascii=False))
    print(report)
