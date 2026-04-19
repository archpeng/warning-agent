from __future__ import annotations

import json
from pathlib import Path

from app.feedback.corpus import assemble_feedback_compare_corpus
from app.storage.artifact_store import JSONLArtifactStore


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    corpus = assemble_feedback_compare_corpus(
        artifact_store=JSONLArtifactStore(root=repo_root / "data"),
        repo_root=repo_root,
    )
    print(json.dumps(corpus["corpus_contract"], indent=2, ensure_ascii=False))
