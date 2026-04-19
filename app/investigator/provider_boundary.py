"""Provider boundary configuration for deterministic smoke vs future real adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

import yaml

from app.investigator.contracts import RecommendedAction


ProviderMode = Literal["deterministic_smoke", "future_real_adapter"]


@dataclass(frozen=True)
class ProviderBoundary:
    mode: ProviderMode
    fail_closed_recommended_action: RecommendedAction


@dataclass(frozen=True)
class ProviderBoundaryConfig:
    local_primary: ProviderBoundary
    cloud_fallback: ProviderBoundary



def _load_boundary(payload: dict[str, object], key: str) -> ProviderBoundary:
    boundary = payload.get(key) or {}
    return ProviderBoundary(
        mode=cast(ProviderMode, str(boundary["mode"])),
        fail_closed_recommended_action=cast(
            RecommendedAction,
            str(boundary["fail_closed_recommended_action"]),
        ),
    )



def load_provider_boundary_config(
    config_path: str | Path = Path("configs/provider-boundary.yaml"),
) -> ProviderBoundaryConfig:
    payload = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    return ProviderBoundaryConfig(
        local_primary=_load_boundary(payload, "local_primary"),
        cloud_fallback=_load_boundary(payload, "cloud_fallback"),
    )
