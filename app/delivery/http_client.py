"""Bounded HTTP client for env-gated adapter delivery bridges."""

from __future__ import annotations

from typing import Final

import httpx

from app.delivery.bridge_result import BridgeDispatchResult

_ACCEPTED_PROVIDER_STATUSES: Final[set[str]] = {"delivered", "duplicate_ignored"}



def post_adapter_feishu_notification(
    *,
    endpoint: str,
    payload: dict[str, object],
    timeout_seconds: int,
) -> BridgeDispatchResult:
    try:
        response = httpx.post(endpoint, json=payload, timeout=float(timeout_seconds))
    except httpx.HTTPError as exc:
        return BridgeDispatchResult(
            status="failed",
            response_code=None,
            provider_key=None,
            provider_status=None,
            message=str(exc),
            external_ref=None,
            raw_response=None,
        )

    try:
        raw_response = response.json()
    except ValueError:
        raw_response = {}

    if not isinstance(raw_response, dict):
        raw_response = {}

    provider_key = str(raw_response.get("providerKey")) if raw_response.get("providerKey") is not None else None
    provider_status = str(raw_response.get("status")) if raw_response.get("status") is not None else None
    external_ref = str(raw_response.get("externalRef")) if raw_response.get("externalRef") is not None else None
    accepted = (
        response.status_code == 202
        and raw_response.get("code") == 0
        and provider_status in _ACCEPTED_PROVIDER_STATUSES
    )
    if accepted:
        return BridgeDispatchResult(
            status="delivered",
            response_code=response.status_code,
            provider_key=provider_key,
            provider_status=provider_status,
            message=None,
            external_ref=external_ref,
            raw_response=raw_response,
        )

    return BridgeDispatchResult(
        status="failed",
        response_code=response.status_code,
        provider_key=provider_key,
        provider_status=provider_status,
        message="adapter_feishu_rejected",
        external_ref=external_ref,
        raw_response=raw_response,
    )
