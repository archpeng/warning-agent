"""Bounded OpenAI-compatible real adapter for local-primary investigation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.analyzer.base import round_score
from app.investigator.base import InvestigationRequest
from app.investigator.contracts import InvestigationResult

_NON_ALNUM = re.compile(r"[^a-z0-9]+")



def _slug_component(value: str) -> str:
    return _NON_ALNUM.sub("_", value.lower()).strip("_")



def _build_investigation_id(packet: dict[str, object], *, offset_seconds: int = 4) -> str:
    created_at = str(packet["created_at"])
    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00")).astimezone(UTC) + timedelta(
        seconds=offset_seconds
    )
    timestamp = dt.strftime("%Y%m%dt%H%M%Sz")
    service = _slug_component(str(packet["service"]))
    operation = _slug_component(str(packet.get("operation") or "service"))
    return f"cir_{service}_{operation}_{timestamp}"



def _generated_at(packet: dict[str, object]) -> str:
    return (
        datetime.fromisoformat(str(packet["created_at"]).replace("Z", "+00:00"))
        .astimezone(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )



def _top_error_template(packet: dict[str, object]) -> str:
    signoz = packet.get("signoz") or {}
    templates = signoz.get("top_error_templates") or []
    if templates and isinstance(templates[0], dict) and templates[0].get("template"):
        return str(templates[0]["template"])
    return "bounded local-primary real adapter response requires operator review"



def _default_reason_codes(request: InvestigationRequest) -> list[str]:
    reason_codes = list(request.decision["reason_codes"][:4])
    return reason_codes or ["local_primary_real_adapter"]



def _default_suspected_code_paths(request: InvestigationRequest) -> list[str]:
    if request.code_search_refs:
        return list(request.code_search_refs[:3])
    packet = request.packet
    service = str(packet["service"])
    operation = str(packet.get("operation") or service)
    repo_candidates = list(packet["topology"]["repo_candidates"])
    return [
        f"services/{service}/{_slug_component(operation)}.py",
        *[f"repos/{candidate}/{_slug_component(operation)}" for candidate in repo_candidates[:2]],
    ][:3]



def _default_routing(request: InvestigationRequest) -> dict[str, object]:
    packet = request.packet
    return {
        "owner_hint": packet["topology"]["owner"],
        "repo_candidates": list(packet["topology"]["repo_candidates"]),
        "suspected_code_paths": _default_suspected_code_paths(request),
        "escalation_target": packet["topology"]["owner"],
    }



def _default_evidence_refs(request: InvestigationRequest) -> dict[str, list[str]]:
    return {
        "prometheus_ref_ids": list(request.prometheus_query_refs),
        "signoz_ref_ids": list(dict.fromkeys([*request.signoz_query_refs, *request.sample_log_refs])),
        "trace_ids": list(request.sample_trace_ids),
        "code_refs": list(request.code_search_refs) or _default_suspected_code_paths(request)[:2],
    }



def _bounded_payload(request: InvestigationRequest) -> dict[str, object]:
    packet = request.packet
    decision = request.decision
    return {
        "packet": {
            "packet_id": packet["packet_id"],
            "service": packet["service"],
            "operation": packet.get("operation") or packet["service"],
            "created_at": packet["created_at"],
            "candidate_source": packet.get("candidate_source"),
            "owner": packet["topology"]["owner"],
            "repo_candidates": list(packet["topology"]["repo_candidates"][:3]),
            "top_error_template": _top_error_template(packet),
        },
        "decision": {
            "decision_id": decision["decision_id"],
            "severity_band": decision["severity_band"],
            "recommended_action": decision["recommended_action"],
            "confidence": decision["confidence"],
            "reason_codes": _default_reason_codes(request),
        },
        "request_bounds": {
            "retrieval_packet_ids": list(request.retrieval_packet_ids),
            "prometheus_query_refs": list(request.prometheus_query_refs),
            "signoz_query_refs": list(request.signoz_query_refs),
            "sample_trace_ids": list(request.sample_trace_ids),
            "sample_log_refs": list(request.sample_log_refs),
            "code_search_refs": list(request.code_search_refs),
            "budget": {
                "wall_time_seconds": request.budget.wall_time_seconds,
                "max_tool_calls": request.budget.max_tool_calls,
                "max_prompt_tokens": request.budget.max_prompt_tokens,
                "max_completion_tokens": request.budget.max_completion_tokens,
            },
        },
        "required_output_contract": {
            "summary": {
                "severity_band": "P1|P2|P3|P4",
                "recommended_action": "observe|open_ticket|page_owner|send_to_human_review",
                "confidence": "0.0-1.0",
                "reason_codes": ["<=4 reason codes"],
                "suspected_primary_cause": "string",
                "failure_chain_summary": "string",
            },
            "hypotheses": [
                {
                    "hypothesis": "string",
                    "confidence": "0.0-1.0",
                    "supporting_reason_codes": ["list of strings"],
                }
            ],
            "routing": {
                "owner_hint": "string|null",
                "repo_candidates": ["list of strings"],
                "suspected_code_paths": ["list of strings"],
                "escalation_target": "string|null",
            },
            "evidence_refs": {
                "prometheus_ref_ids": ["list of strings"],
                "signoz_ref_ids": ["list of strings"],
                "trace_ids": ["list of strings"],
                "code_refs": ["list of strings"],
            },
            "unknowns": ["list of strings"],
            "analysis_updates": {
                "notes": ["list of strings"],
                "severity_band_changed": "bool",
                "recommended_action_changed": "bool",
                "fallback_invocation_was_correct": "bool|null",
            },
        },
    }



def _build_messages(request: InvestigationRequest) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are warning-agent local_primary real adapter. "
                "Return one JSON object only. Do not include markdown fences. "
                "Do not invent unbounded evidence beyond the provided request bounds."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(_bounded_payload(request), ensure_ascii=False),
        },
    ]



def _extract_text_content(message_content: Any) -> str:
    if isinstance(message_content, str):
        return message_content.strip()
    if isinstance(message_content, list):
        parts: list[str] = []
        for item in message_content:
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                parts.append(item["text"].strip())
        joined = "\n".join(part for part in parts if part)
        if joined:
            return joined
    raise RuntimeError("local_primary real adapter response missing text content")



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



def _coerce_hypotheses(value: object, *, default_reason_codes: list[str], default_cause: str) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value:
        return [
            {
                "rank": 1,
                "hypothesis": default_cause,
                "confidence": 0.5,
                "supporting_reason_codes": list(default_reason_codes),
            }
        ]

    hypotheses: list[dict[str, object]] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            continue
        hypothesis = str(item.get("hypothesis") or default_cause).strip()
        confidence_value = item.get("confidence")
        try:
            confidence = round_score(float(confidence_value))
        except (TypeError, ValueError):
            confidence = 0.5
        supporting_reason_codes = _coerce_string_list(
            item.get("supporting_reason_codes"),
            default=default_reason_codes,
        )
        hypotheses.append(
            {
                "rank": index,
                "hypothesis": hypothesis,
                "confidence": confidence,
                "supporting_reason_codes": supporting_reason_codes or list(default_reason_codes),
            }
        )
    return hypotheses or [
        {
            "rank": 1,
            "hypothesis": default_cause,
            "confidence": 0.5,
            "supporting_reason_codes": list(default_reason_codes),
        }
    ]



def _coerce_routing(value: object, *, default: dict[str, object]) -> dict[str, object]:
    if not isinstance(value, dict):
        return default
    return {
        "owner_hint": value.get("owner_hint") if value.get("owner_hint") is not None else default["owner_hint"],
        "repo_candidates": _coerce_string_list(value.get("repo_candidates"), default=list(default["repo_candidates"])),
        "suspected_code_paths": _coerce_string_list(
            value.get("suspected_code_paths"),
            default=list(default["suspected_code_paths"]),
        ),
        "escalation_target": (
            value.get("escalation_target") if value.get("escalation_target") is not None else default["escalation_target"]
        ),
    }



def _coerce_evidence_refs(value: object, *, default: dict[str, list[str]]) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return default
    return {
        "prometheus_ref_ids": _coerce_string_list(value.get("prometheus_ref_ids"), default=default["prometheus_ref_ids"]),
        "signoz_ref_ids": _coerce_string_list(value.get("signoz_ref_ids"), default=default["signoz_ref_ids"]),
        "trace_ids": _coerce_string_list(value.get("trace_ids"), default=default["trace_ids"]),
        "code_refs": _coerce_string_list(value.get("code_refs"), default=default["code_refs"]),
    }



def _coerce_analysis_updates(value: object) -> dict[str, object]:
    notes = ["local_primary_real_adapter_response_mapped", "local_primary_real_adapter_transport=openai_compatible_http"]
    if not isinstance(value, dict):
        return {
            "severity_band_changed": False,
            "recommended_action_changed": False,
            "fallback_invocation_was_correct": None,
            "notes": notes,
        }
    extra_notes = _coerce_string_list(value.get("notes"), default=[])
    return {
        "severity_band_changed": bool(value.get("severity_band_changed", False)),
        "recommended_action_changed": bool(value.get("recommended_action_changed", False)),
        "fallback_invocation_was_correct": value.get("fallback_invocation_was_correct"),
        "notes": [*extra_notes, *notes],
    }



def _decode_response_payload(payload: dict[str, object]) -> dict[str, object]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("local_primary real adapter response missing choices")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise RuntimeError("local_primary real adapter choice must be a mapping")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise RuntimeError("local_primary real adapter response missing message payload")
    content = _extract_text_content(message.get("content"))
    decoded = json.loads(_strip_code_fence(content))
    if not isinstance(decoded, dict):
        raise RuntimeError("local_primary real adapter JSON content must be an object")
    return decoded



def _map_response_to_result(
    response_payload: dict[str, object],
    *,
    request: InvestigationRequest,
    model_provider: str,
    model_name: str,
) -> InvestigationResult:
    packet = request.packet
    decision = request.decision
    default_reason_codes = _default_reason_codes(request)
    default_routing = _default_routing(request)
    default_evidence_refs = _default_evidence_refs(request)
    decoded = _decode_response_payload(response_payload)

    summary_payload = decoded.get("summary") if isinstance(decoded.get("summary"), dict) else {}
    suspected_primary_cause = str(
        summary_payload.get("suspected_primary_cause") or _top_error_template(packet)
    ).strip()
    failure_chain_summary = str(
        summary_payload.get("failure_chain_summary")
        or f"local-primary real adapter investigated {packet['service']} and kept {suspected_primary_cause} as the leading cause."
    ).strip()
    try:
        confidence = round_score(float(summary_payload.get("confidence", decision["confidence"])))
    except (TypeError, ValueError):
        confidence = round_score(float(decision["confidence"]))

    reason_codes = _coerce_string_list(summary_payload.get("reason_codes"), default=default_reason_codes)
    hypotheses = _coerce_hypotheses(
        decoded.get("hypotheses"),
        default_reason_codes=reason_codes or default_reason_codes,
        default_cause=suspected_primary_cause,
    )

    return {
        "schema_version": "investigation-result.v1",
        "investigation_id": _build_investigation_id(packet),
        "packet_id": str(packet["packet_id"]),
        "decision_id": str(decision["decision_id"]),
        "investigator_tier": "local_primary_investigator",
        "model_provider": model_provider,
        "model_name": model_name,
        "generated_at": _generated_at(packet),
        "input_refs": {
            "packet_id": str(packet["packet_id"]),
            "decision_id": str(decision["decision_id"]),
            "retrieval_packet_ids": list(request.retrieval_packet_ids),
            "prometheus_query_refs": list(request.prometheus_query_refs),
            "signoz_query_refs": list(request.signoz_query_refs),
            "code_search_refs": list(request.code_search_refs),
            "upstream_report_id": None,
        },
        "summary": {
            "investigation_used": True,
            "severity_band": str(summary_payload.get("severity_band") or decision["severity_band"]),
            "recommended_action": str(
                summary_payload.get("recommended_action") or decision["recommended_action"]
            ),
            "confidence": confidence,
            "reason_codes": reason_codes or default_reason_codes,
            "suspected_primary_cause": suspected_primary_cause,
            "failure_chain_summary": failure_chain_summary,
        },
        "hypotheses": hypotheses,
        "analysis_updates": _coerce_analysis_updates(decoded.get("analysis_updates")),
        "routing": _coerce_routing(decoded.get("routing"), default=default_routing),
        "evidence_refs": _coerce_evidence_refs(decoded.get("evidence_refs"), default=default_evidence_refs),
        "unknowns": _coerce_string_list(
            decoded.get("unknowns"),
            default=["local-primary real adapter returned bounded output without deeper tool corroboration"],
        ),
    }


@dataclass(frozen=True)
class LocalPrimaryOpenAICompatibleProvider:
    endpoint: str
    model_name: str
    timeout_seconds: int
    api_key: str | None = None
    model_provider: str = "local_vllm"
    provider_name: str = "local_primary"

    def investigate(self, request: InvestigationRequest) -> InvestigationResult:
        url = f"{self.endpoint.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model_name,
            "temperature": 0,
            "messages": _build_messages(request),
        }

        response = httpx.post(url, json=payload, headers=headers, timeout=float(self.timeout_seconds))
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise RuntimeError("local_primary real adapter HTTP response must be a JSON object")
        return _map_response_to_result(
            body,
            request=request,
            model_provider=self.model_provider,
            model_name=self.model_name,
        )
