"""Bounded OpenAI Responses API real adapter for cloud-fallback investigation."""

from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from app.analyzer.base import round_score
from app.investigator.cloud_fallback_brief import (
    CloudFallbackClientRequest,
    CloudFallbackClientResponse,
    CloudFallbackHypothesis,
    parse_cloud_handoff_markdown,
)


SYSTEM_PROMPT = (
    "You are warning-agent cloud_fallback real adapter. "
    "Review only the bounded local-primary handoff and return one JSON object. "
    "Do not include markdown fences. Do not invent unbounded evidence beyond the supplied handoff and refs."
)


def _inline_or_none(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "none"



def _build_bounded_payload(request: CloudFallbackClientRequest) -> dict[str, object]:
    handoff = parse_cloud_handoff_markdown(request.handoff_markdown)
    return {
        "handoff": {
            "packet_id": request.packet_id,
            "decision_id": request.decision_id,
            "parent_investigation_id": request.parent_investigation_id,
            "service": handoff.get("service"),
            "operation": handoff.get("operation"),
            "severity_band": handoff.get("severity_band"),
            "recommended_action": handoff.get("recommended_action"),
            "parent_confidence": handoff.get("parent_confidence"),
            "suspected_primary_cause": handoff.get("suspected_primary_cause"),
            "top_hypothesis": handoff.get("top_hypothesis"),
            "local_unknowns": handoff.get("local_unknowns"),
        },
        "request_bounds": {
            "handoff_tokens_estimate": request.handoff_tokens_estimate,
            "carry_reason_codes": list(request.carry_reason_codes[:4]),
            "retrieval_packet_ids": list(request.retrieval_packet_ids[:3]),
            "prometheus_query_refs": list(request.prometheus_query_refs[:3]),
            "signoz_query_refs": list(request.signoz_query_refs[:3]),
            "trace_ids": list(request.trace_ids[:3]),
            "repo_candidates": list(request.repo_candidates[:3]),
            "code_refs": list(request.code_refs[:3]),
        },
        "required_output_contract": {
            "severity_band": "P1|P2|P3|P4",
            "recommended_action": "observe|open_ticket|page_owner|send_to_human_review",
            "confidence": "0.0-1.0",
            "suspected_primary_cause": "string",
            "failure_chain_summary": "string",
            "hypotheses": [
                {
                    "hypothesis": "string",
                    "confidence": "0.0-1.0",
                    "supporting_reason_codes": ["list of strings"],
                }
            ],
            "unknowns": ["list of strings"],
            "notes": ["list of strings"],
        },
    }



def _build_input(request: CloudFallbackClientRequest) -> list[dict[str, object]]:
    return [
        {
            "role": "system",
            "content": [
                {
                    "type": "input_text",
                    "text": SYSTEM_PROMPT,
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": json.dumps(_build_bounded_payload(request), ensure_ascii=False),
                }
            ],
        },
    ]



def _extract_output_text(payload: dict[str, object]) -> str:
    direct_text = payload.get("output_text")
    if isinstance(direct_text, str) and direct_text.strip():
        return direct_text.strip()

    output = payload.get("output")
    if not isinstance(output, list):
        raise RuntimeError("cloud_fallback real adapter response missing output payload")

    parts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for content_item in content:
            if not isinstance(content_item, dict):
                continue
            if content_item.get("type") != "output_text":
                continue
            text = content_item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
    if not parts:
        raise RuntimeError("cloud_fallback real adapter response missing output_text content")
    return "\n".join(parts)



def _strip_code_fence(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return stripped



def _coerce_string_list(value: object, *, default: list[str]) -> list[str]:
    if not isinstance(value, list):
        return list(default)
    return [str(item) for item in value if str(item).strip()]



def _default_reason_codes(request: CloudFallbackClientRequest) -> list[str]:
    return list(request.carry_reason_codes[:4]) or ["cloud_fallback_real_adapter"]



def _default_unknowns(request: CloudFallbackClientRequest) -> list[str]:
    handoff = parse_cloud_handoff_markdown(request.handoff_markdown)
    local_unknowns = handoff.get("local_unknowns") or "none"
    if local_unknowns == "none":
        return ["bounded cloud fallback real adapter returned no additional unknowns"]
    return [part.strip() for part in local_unknowns.split(",") if part.strip()]



def _default_hypothesis(request: CloudFallbackClientRequest) -> str:
    handoff = parse_cloud_handoff_markdown(request.handoff_markdown)
    suspected_cause = handoff.get(
        "suspected_primary_cause",
        "local-primary handoff remained unresolved before bounded cloud review",
    )
    service = handoff.get("service", "unknown-service")
    operation = handoff.get("operation", service)
    return f"cloud fallback confirms {suspected_cause} as the most likely driver of the {service} regression on {operation}"



def _coerce_hypotheses(
    value: object,
    *,
    request: CloudFallbackClientRequest,
    default_reason_codes: list[str],
) -> tuple[CloudFallbackHypothesis, ...]:
    if not isinstance(value, list) or not value:
        return (
            CloudFallbackHypothesis(
                hypothesis=_default_hypothesis(request),
                confidence=0.5,
                supporting_reason_codes=tuple(default_reason_codes),
            ),
        )

    hypotheses: list[CloudFallbackHypothesis] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        try:
            confidence = round_score(float(item.get("confidence", 0.5)))
        except (TypeError, ValueError):
            confidence = 0.5
        supporting_reason_codes = tuple(
            _coerce_string_list(item.get("supporting_reason_codes"), default=default_reason_codes)
        )
        hypotheses.append(
            CloudFallbackHypothesis(
                hypothesis=str(item.get("hypothesis") or _default_hypothesis(request)).strip(),
                confidence=confidence,
                supporting_reason_codes=supporting_reason_codes or tuple(default_reason_codes),
            )
        )
    return tuple(hypotheses) or (
        CloudFallbackHypothesis(
            hypothesis=_default_hypothesis(request),
            confidence=0.5,
            supporting_reason_codes=tuple(default_reason_codes),
        ),
    )



def _decode_response(payload: dict[str, object]) -> dict[str, object]:
    text = _extract_output_text(payload)
    decoded = json.loads(_strip_code_fence(text))
    if not isinstance(decoded, dict):
        raise RuntimeError("cloud_fallback real adapter JSON content must be an object")
    return decoded



def _map_response_to_client_response(
    payload: dict[str, object],
    *,
    request: CloudFallbackClientRequest,
) -> CloudFallbackClientResponse:
    decoded = _decode_response(payload)
    handoff = parse_cloud_handoff_markdown(request.handoff_markdown)
    default_reason_codes = _default_reason_codes(request)

    severity_band = str(decoded.get("severity_band") or handoff.get("severity_band") or "P3")
    recommended_action = str(
        decoded.get("recommended_action") or handoff.get("recommended_action") or "send_to_human_review"
    )
    try:
        confidence = round_score(float(decoded.get("confidence", handoff.get("parent_confidence") or 0.55)))
    except (TypeError, ValueError):
        confidence = 0.55
    suspected_primary_cause = str(
        decoded.get("suspected_primary_cause")
        or handoff.get("suspected_primary_cause")
        or "local-primary handoff remained unresolved before bounded cloud review"
    ).strip()
    failure_chain_summary = str(
        decoded.get("failure_chain_summary")
        or (
            f"cloud fallback reviewed the bounded local handoff and retained {suspected_primary_cause} as the leading failure chain driver."
        )
    ).strip()
    unknowns = tuple(_coerce_string_list(decoded.get("unknowns"), default=_default_unknowns(request)))
    notes = tuple(
        [
            *_coerce_string_list(decoded.get("notes"), default=[]),
            "cloud_fallback_real_adapter_runtime_invoked",
            "cloud_fallback_real_adapter_response_mapped",
            "cloud_fallback_real_adapter_transport=openai_responses_api",
            f"handoff_tokens_estimate={request.handoff_tokens_estimate}",
            f"bounded_repo_candidates={_inline_or_none(request.repo_candidates[:3])}",
        ]
    )
    hypotheses = _coerce_hypotheses(
        decoded.get("hypotheses"),
        request=request,
        default_reason_codes=default_reason_codes,
    )

    return CloudFallbackClientResponse(
        severity_band=severity_band,
        recommended_action=recommended_action,
        confidence=confidence,
        suspected_primary_cause=suspected_primary_cause,
        failure_chain_summary=failure_chain_summary,
        hypotheses=hypotheses,
        unknowns=unknowns,
        notes=notes,
    )


@dataclass(frozen=True)
class CloudFallbackOpenAIResponsesClient:
    endpoint: str
    api_key: str
    model_name: str
    timeout_seconds: int
    model_provider: str = "neko_api_openai"
    provider_name: str = "cloud_fallback"

    def investigate(self, request: CloudFallbackClientRequest) -> CloudFallbackClientResponse:
        url = f"{self.endpoint.rstrip('/')}/responses"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model_name,
            "input": _build_input(request),
        }
        response = httpx.post(url, json=payload, headers=headers, timeout=float(self.timeout_seconds))
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise RuntimeError("cloud_fallback real adapter HTTP response must be a JSON object")
        return _map_response_to_client_response(body, request=request)
