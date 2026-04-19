from __future__ import annotations

import json
from pathlib import Path

from app.live_runtime_smoke import run_live_runtime_smoke
from app.storage.artifact_store import JSONLArtifactStore


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    summary = run_live_runtime_smoke(
        "fixtures/replay/manual-replay.checkout.high-error-rate.json",
        repo_root=repo_root,
        artifact_store=JSONLArtifactStore(root=repo_root / "data"),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
