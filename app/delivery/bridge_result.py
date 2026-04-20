"""Result contract for env-gated live delivery bridge attempts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class BridgeDispatchResult:
    status: Literal["delivered", "failed"]
    response_code: int | None
    provider_key: str | None
    provider_status: str | None
    message: str | None
    external_ref: str | None
    raw_response: dict[str, object] | None
