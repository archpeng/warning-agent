"""Shared helpers for materialized warning-agent runtime contracts."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
SCHEMA_DIR: Final[Path] = REPO_ROOT / "schemas"
DATA_DIR: Final[Path] = REPO_ROOT / "data"


def schema_path(file_name: str) -> Path:
    return SCHEMA_DIR / file_name


@lru_cache(maxsize=None)
def load_json_schema(file_name: str) -> dict[str, Any]:
    with schema_path(file_name).open("r", encoding="utf-8") as handle:
        return json.load(handle)
