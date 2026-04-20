"""Governed Signoz warning ingress surface for warning-agent."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, Final, Literal, TypedDict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.receiver.signoz_alert import (
    SignozAlertPayload,
    missing_required_signoz_fields,
    normalize_signoz_alert_payload,
)
from app.storage.signoz_warning_store import SignozWarningStore, _utc_now

SIGNOZ_INGRESS_PATH: Final = "/webhook/signoz"
SIGNOZ_INGRESS_RECEIPT_SCHEMA_VERSION: Final = "signoz-warning-ingress-receipt.v1"
SIGNOZ_CALLER_HEADER: Final = "X-Warning-Agent-Caller"
SIGNOZ_SHARED_TOKEN_ENV: Final = "WARNING_AGENT_SIGNOZ_INGRESS_SHARED_TOKEN"


class SignozIngressCaller(TypedDict):
    caller_id: str
    auth_mode: Literal["shared_token"]


class SignozIngressProvenance(TypedDict):
    remote_source: Literal["signoz_webhook"]
    received_at: str
    remote_addr: str | None
    rule_id: str | None
    source_url: str | None
    eval_window: str | None
    starts_at: str | None
    ends_at: str | None


class SignozIngressError(TypedDict):
    code: str
    message: str


class SignozIngressReceipt(TypedDict, total=False):
    schema_version: str
    accepted: bool
    receipt_state: Literal["accepted", "rejected", "deferred"]
    warning_id: str | None
    normalized: dict[str, Any]
    caller: SignozIngressCaller
    provenance: SignozIngressProvenance
    raw_payload_path: str | None
    normalized_alert_path: str | None
    receipt_path: str | None
    index_db_path: str | None
    queue: dict[str, Any]
    error: SignozIngressError


@dataclass(frozen=True)
class SignozIngressAuthResolution:
    state: Literal["ready", "missing_env"]
    shared_token_env: str


@dataclass(frozen=True)
class SignozIngressIdentity:
    caller_id: str
    auth_mode: Literal["shared_token"] = "shared_token"



def resolve_signoz_ingress_auth(*, env: dict[str, str] | None = None) -> SignozIngressAuthResolution:
    env = env or {}
    token = env.get(SIGNOZ_SHARED_TOKEN_ENV)
    return SignozIngressAuthResolution(
        state="ready" if isinstance(token, str) and token else "missing_env",
        shared_token_env=SIGNOZ_SHARED_TOKEN_ENV,
    )



def _authorization_token(request: Request) -> str | None:
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return token or None



def authenticate_signoz_request(
    request: Request,
    *,
    env: dict[str, str] | None = None,
) -> SignozIngressIdentity | None:
    env = env or {}
    caller_id = request.headers.get(SIGNOZ_CALLER_HEADER)
    if not caller_id:
        raise PermissionError(f"missing required caller header: {SIGNOZ_CALLER_HEADER}")

    expected_token = env.get(SIGNOZ_SHARED_TOKEN_ENV)
    if not expected_token:
        return None

    provided_token = _authorization_token(request)
    if provided_token != expected_token:
        raise PermissionError("shared token authentication failed")

    return SignozIngressIdentity(caller_id=caller_id)



def build_signoz_provenance(
    normalized: dict[str, Any],
    *,
    received_at: str,
    remote_addr: str | None,
) -> SignozIngressProvenance:
    refs = normalized.get("source_refs") or {}
    return {
        "remote_source": "signoz_webhook",
        "received_at": received_at,
        "remote_addr": remote_addr,
        "rule_id": _string_or_none(refs.get("rule_id")),
        "source_url": _string_or_none(refs.get("source_url")),
        "eval_window": _string_or_none(refs.get("eval_window")),
        "starts_at": _string_or_none(refs.get("starts_at")),
        "ends_at": _string_or_none(refs.get("ends_at")),
    }



def build_signoz_ingress_receipt(
    *,
    normalized: dict[str, Any],
    caller: SignozIngressIdentity,
    provenance: SignozIngressProvenance,
    receipt_state: Literal["accepted", "rejected", "deferred"],
    warning_id: str | None = None,
    raw_payload_path: str | None = None,
    normalized_alert_path: str | None = None,
    receipt_path: str | None = None,
    index_db_path: str | None = None,
    error: SignozIngressError | None = None,
) -> SignozIngressReceipt:
    receipt: SignozIngressReceipt = {
        "schema_version": SIGNOZ_INGRESS_RECEIPT_SCHEMA_VERSION,
        "accepted": receipt_state == "accepted",
        "receipt_state": receipt_state,
        "warning_id": warning_id,
        "normalized": normalized,
        "caller": asdict(caller),
        "provenance": provenance,
        "raw_payload_path": raw_payload_path,
        "normalized_alert_path": normalized_alert_path,
        "receipt_path": receipt_path,
        "index_db_path": index_db_path,
    }
    if error is not None:
        receipt["error"] = error
    return receipt



def build_signoz_ingress_router(
    *,
    warning_store: SignozWarningStore | None = None,
    post_accept_handler: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
    env: dict[str, str] | None = None,
    now_provider: Callable[[], str] | None = None,
) -> APIRouter:
    env = env or {}
    router = APIRouter()

    @router.post(SIGNOZ_INGRESS_PATH, response_model=None)
    def receive_signoz_warning(payload: SignozAlertPayload, request: Request):
        missing_fields = missing_required_signoz_fields(payload)
        if missing_fields:
            normalized = normalize_signoz_alert_payload(payload)
            provenance = build_signoz_provenance(
                normalized,
                received_at=(now_provider() if now_provider else _utc_now()),
                remote_addr=request.client.host if request.client else None,
            )
            caller_id = request.headers.get(SIGNOZ_CALLER_HEADER, "unknown")
            receipt = build_signoz_ingress_receipt(
                normalized=normalized,
                caller=SignozIngressIdentity(caller_id=caller_id),
                provenance=provenance,
                receipt_state="rejected",
                error={
                    "code": "payload_validation_error",
                    "message": f"missing required fields: {', '.join(missing_fields)}",
                },
            )
            return JSONResponse(status_code=422, content=receipt)

        normalized = normalize_signoz_alert_payload(payload)
        received_at = now_provider() if now_provider else _utc_now()
        provenance = build_signoz_provenance(
            normalized,
            received_at=received_at,
            remote_addr=request.client.host if request.client else None,
        )

        auth_resolution = resolve_signoz_ingress_auth(env=env)
        try:
            caller = authenticate_signoz_request(request, env=env)
        except PermissionError as exc:
            fallback_caller = SignozIngressIdentity(caller_id=request.headers.get(SIGNOZ_CALLER_HEADER, "unknown"))
            receipt = build_signoz_ingress_receipt(
                normalized=normalized,
                caller=fallback_caller,
                provenance=provenance,
                receipt_state="rejected",
                error={
                    "code": "auth_failed",
                    "message": str(exc),
                },
            )
            return JSONResponse(status_code=401, content=receipt)

        assert caller is not None or auth_resolution.state == "missing_env"
        caller = caller or SignozIngressIdentity(caller_id=request.headers.get(SIGNOZ_CALLER_HEADER, "unknown"))

        if auth_resolution.state != "ready":
            receipt = build_signoz_ingress_receipt(
                normalized=normalized,
                caller=caller,
                provenance=provenance,
                receipt_state="deferred",
                error={
                    "code": "ingress_auth_unconfigured",
                    "message": f"missing required ingress auth env: {SIGNOZ_SHARED_TOKEN_ENV}",
                },
            )
            return JSONResponse(status_code=503, content=receipt)

        if normalized.get("status") != "firing":
            receipt = build_signoz_ingress_receipt(
                normalized=normalized,
                caller=caller,
                provenance=provenance,
                receipt_state="deferred",
                error={
                    "code": "warning_not_firing",
                    "message": "only firing Signoz warnings are accepted for admission",
                },
            )
            return JSONResponse(status_code=202, content=receipt)

        receipt = build_signoz_ingress_receipt(
            normalized=normalized,
            caller=caller,
            provenance=provenance,
            receipt_state="accepted",
        )
        if warning_store is None:
            return JSONResponse(status_code=202, content=receipt)

        try:
            persisted = warning_store.persist_admission(
                raw_payload=dict(payload),
                normalized_alert=normalized,
                receipt=receipt,
            )
        except Exception as exc:
            deferred_receipt = build_signoz_ingress_receipt(
                normalized=normalized,
                caller=caller,
                provenance=provenance,
                receipt_state="deferred",
                error={
                    "code": "admission_unavailable",
                    "message": str(exc),
                },
            )
            return JSONResponse(status_code=503, content=deferred_receipt)

        if post_accept_handler is not None:
            try:
                queue_result = post_accept_handler(persisted)
            except Exception as exc:
                deferred_receipt = {
                    **persisted,
                    "accepted": False,
                    "receipt_state": "deferred",
                    "error": {
                        "code": "queue_unavailable",
                        "message": str(exc),
                    },
                }
                return JSONResponse(status_code=503, content=deferred_receipt)
            if isinstance(queue_result, dict):
                persisted = {
                    **persisted,
                    "queue": queue_result,
                }

        return JSONResponse(status_code=202, content=persisted)

    return router



def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


__all__ = [
    "SIGNOZ_CALLER_HEADER",
    "SIGNOZ_INGRESS_PATH",
    "SIGNOZ_INGRESS_RECEIPT_SCHEMA_VERSION",
    "SIGNOZ_SHARED_TOKEN_ENV",
    "SignozIngressIdentity",
    "SignozIngressReceipt",
    "build_signoz_ingress_receipt",
    "build_signoz_ingress_router",
    "build_signoz_provenance",
    "resolve_signoz_ingress_auth",
]
