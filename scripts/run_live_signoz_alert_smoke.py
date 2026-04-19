from __future__ import annotations

import json
from pathlib import Path

from app.live_signoz_smoke import run_live_signoz_alert_smoke
from app.storage.artifact_store import JSONLArtifactStore


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    summary = run_live_signoz_alert_smoke(
        "fixtures/replay/signoz-alert.prod-hq-bff-service.error.json",
        repo_root=repo_root,
        artifact_store=JSONLArtifactStore(root=repo_root / "data"),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
