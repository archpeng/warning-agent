from __future__ import annotations

import json
from pathlib import Path

from app.feedback.compare import run_feedback_retrain_compare


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    summary = run_feedback_retrain_compare(repo_root=repo_root)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
