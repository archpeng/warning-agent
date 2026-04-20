"""Deterministic local-primary investigator smoke provider."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Mapping
from urllib.parse import parse_qs, unquote, urlparse

from app.analyzer.base import round_score
from app.investigator.base import InvestigationRequest, InvestigatorBudget, ProviderName
from app.investigator.contracts import InvestigationResult
from app.investigator.local_primary_resident import (
    LocalPrimaryAbnormalPathDecision,
    LocalPrimaryPrewarmSource,
    LocalPrimaryResidentLifecycle,
    LocalPrimaryResidentResolution,
    LocalPrimaryRuntimeContext,
    RealAdapterProviderProtocol,
    decide_local_primary_abnormal_path,
    local_primary_abnormal_path_payload,
    local_primary_resident_lifecycle_payload,
    prewarm_local_primary_resident_service as _prewarm_local_primary_resident_service,
    reset_local_primary_resident_service as _reset_local_primary_resident_service,
)
from app.investigator.provider_boundary import (
    ProviderBoundary,
    ResolvedRealAdapterGate,
    load_provider_boundary_config,
    resolve_real_adapter_gate,
)
from app.investigator.router import load_investigator_routing_config
from app.investigator.tools import BoundedInvestigatorTools

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _slug_component(value: str) -> str:
    return _NON_ALNUM.sub("_", value.lower()).strip("_")


def build_investigation_id(packet: dict[str, object], *, offset_seconds: int = 4) -> str:
    created_at = str(packet["created_at"])
    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00")).astimezone(UTC) + timedelta(
        seconds=offset_seconds
    )
    timestamp = dt.strftime("%Y%m%dt%H%M%Sz")
    service = _slug_component(str(packet["service"]))
    operation = _slug_component(str(packet.get("operation") or "service"))
    return f"cir_{service}_{operation}_{timestamp}"


def _is_live_evidence_request(request: InvestigationRequest) -> bool:
    return any(ref.startswith("promql://") for ref in request.prometheus_query_refs) or any(
        ref.startswith("signoz-mcp://") for ref in request.signoz_query_refs
    )


def _is_signoz_first_packet(packet: dict[str, object]) -> bool:
    return packet.get("candidate_source") == "signoz_alert" or bool(packet["signoz"].get("alert_context"))


def _parse_promql_ref(ref: str) -> tuple[str | None, str | None]:
    parsed = urlparse(ref)
    if parsed.scheme != "promql":
        return None, None
    params = parse_qs(parsed.query)
    endpoint = params.get("endpoint", [None])[0]
    query = params.get("query", [None])[0]
    return endpoint, unquote(query) if query is not None else None


def _packet_trace_detail_hints(packet: dict[str, object]) -> list[dict[str, str | None]]:
    hints = packet["signoz"].get("trace_detail_hints") or []
    return [hint for hint in hints if isinstance(hint, dict)]


def _trace_hint_target(hint: dict[str, str | None]) -> str | None:
    return hint.get("service_name") or hint.get("target")


def _trace_hint_summary(hint: dict[str, str | None]) -> str:
    target = _trace_hint_target(hint) or "unknown target"
    span_name = hint.get("span_name") or "unknown span"
    status_code = hint.get("status_code") or "unknown"
    return f"{target} via {span_name} returned {status_code}"


def reset_local_primary_resident_service() -> None:
    _reset_local_primary_resident_service()



def prewarm_local_primary_resident_service(
    *,
    config_path: str | Path = Path("configs/escalation.yaml"),
    repo_root: str | Path = Path("."),
    env: Mapping[str, str | None] = os.environ,
    prewarm_source: LocalPrimaryPrewarmSource = "provider_init",
    real_adapter_provider: RealAdapterProviderProtocol | None = None,
) -> LocalPrimaryResidentResolution:
    return _prewarm_local_primary_resident_service(
        config_path=config_path,
        repo_root=repo_root,
        env=env,
        prewarm_source=prewarm_source,
        real_adapter_provider=real_adapter_provider,
        build_real_provider=lambda boundary, gate, model_provider: build_real_local_primary_provider(
            boundary=boundary,
            gate=gate,
            model_provider=model_provider,
        ),
    )


def build_real_local_primary_provider(
    *,
    boundary: ProviderBoundary,
    gate: ResolvedRealAdapterGate,
    model_provider: str,
) -> RealAdapterProviderProtocol:
    if gate.state != "ready":
        raise ValueError("real local-primary provider can only be built when gate state is ready")
    if gate.transport != "openai_compatible_http":
        raise RuntimeError(f"unsupported local_primary real adapter transport: {gate.transport}")
    if gate.endpoint is None or gate.model_name is None:
        raise RuntimeError("local_primary real adapter gate ready but endpoint/model_name missing")

    from app.investigator.local_primary_openai_compat import LocalPrimaryOpenAICompatibleProvider

    return LocalPrimaryOpenAICompatibleProvider(
        endpoint=gate.endpoint,
        model_name=gate.model_name,
        timeout_seconds=boundary.real_adapter.timeout_seconds,
        api_key=gate.api_key,
        model_provider=model_provider,
    )


@dataclass(frozen=True)
class LocalPrimaryInvestigator:
    budget: InvestigatorBudget
    model_provider: str
    model_name: str
    tools: BoundedInvestigatorTools | None = None
    env: Mapping[str, str | None] = field(default_factory=lambda: os.environ)
    real_adapter_provider: RealAdapterProviderProtocol | None = None
    resident_lifecycle: LocalPrimaryResidentLifecycle | None = None
    provider_boundary_path: Path = Path("configs/provider-boundary.yaml")
    routing_config_path: Path = Path("configs/escalation.yaml")
    repo_root: Path = Path(".")
    provider_name: ProviderName = "local_primary"

    @classmethod
    def from_config(
        cls,
        config_path: str | Path = Path("configs/escalation.yaml"),
        *,
        repo_root: str | Path = Path("."),
        tools: BoundedInvestigatorTools | None = None,
        env: Mapping[str, str | None] = os.environ,
        real_adapter_provider: RealAdapterProviderProtocol | None = None,
    ) -> "LocalPrimaryInvestigator":
        repo_root = Path(repo_root)
        config_path = Path(config_path)
        config = load_investigator_routing_config(config_path)
        resident_resolution = prewarm_local_primary_resident_service(
            config_path=config_path,
            repo_root=repo_root,
            env=env,
            prewarm_source="provider_init",
            real_adapter_provider=real_adapter_provider,
        )
        return cls(
            budget=config.local_primary.budget,
            model_provider=config.local_primary.model_provider,
            model_name=config.local_primary.model_name,
            tools=tools or BoundedInvestigatorTools.from_config(repo_root=repo_root),
            env=env,
            real_adapter_provider=resident_resolution.real_adapter_provider or real_adapter_provider,
            resident_lifecycle=resident_resolution.lifecycle,
            provider_boundary_path=repo_root / "configs" / "provider-boundary.yaml",
            routing_config_path=config_path,
            repo_root=repo_root,
        )

    def investigate(self, request: InvestigationRequest) -> InvestigationResult:
        if request.budget != self.budget:
            raise ValueError("request budget must match local-primary provider budget")

        resident_resolution = prewarm_local_primary_resident_service(
            config_path=self.routing_config_path,
            repo_root=self.repo_root,
            env=self.env,
            prewarm_source="provider_init",
            real_adapter_provider=self.real_adapter_provider,
        )
        resident_lifecycle = resident_resolution.lifecycle
        if resident_lifecycle.state == "not_ready":
            raise RuntimeError(resident_lifecycle.reason or "local_primary resident service not ready")
        if resident_lifecycle.state == "degraded":
            raise RuntimeError(resident_lifecycle.reason or "local_primary resident service degraded")

        boundary = load_provider_boundary_config(self.provider_boundary_path).local_primary
        gate = resolve_real_adapter_gate(boundary, env=self.env)
        if gate.state == "ready":
            real_adapter_provider = resident_resolution.real_adapter_provider or self.real_adapter_provider
            if real_adapter_provider is None:
                real_adapter_provider = build_real_local_primary_provider(
                    boundary=boundary,
                    gate=gate,
                    model_provider=self.model_provider,
                )
            return real_adapter_provider.investigate(request)

        if _is_signoz_first_packet(request.packet):
            return self._investigate_signoz_first(request)
        return self._investigate_legacy(request)

    def _investigate_legacy(self, request: InvestigationRequest) -> InvestigationResult:
        packet = request.packet
        decision = request.decision
        top_template = packet["signoz"]["top_error_templates"][0]
        primary_cause = str(top_template["template"])
        service = str(packet["service"])
        operation = str(packet.get("operation") or service)
        severity_score = float(decision["severity_score"])
        confidence = round_score(min(1.0, float(decision["confidence"]) + 0.14))
        reason_codes = decision["reason_codes"][:4]
        if not reason_codes:
            reason_codes = ["local_primary_smoke"]

        hypotheses = [
            {
                "rank": 1,
                "hypothesis": f"{primary_cause} is driving the {service} regression on {operation}",
                "confidence": round_score(min(0.95, confidence)),
                "supporting_reason_codes": reason_codes,
            }
        ]
        if packet.get("history", {}).get("recent_deploy"):
            hypotheses.append(
                {
                    "rank": 2,
                    "hypothesis": f"recent deploy changed {service} behavior and amplified {primary_cause}",
                    "confidence": round_score(max(0.4, confidence - 0.18)),
                    "supporting_reason_codes": ["recent_deploy"],
                }
            )
        if request.retrieval_packet_ids:
            hypotheses.append(
                {
                    "rank": len(hypotheses) + 1,
                    "hypothesis": f"retrieval history suggests the current {service} issue resembles prior severe incidents",
                    "confidence": round_score(max(0.35, confidence - 0.22)),
                    "supporting_reason_codes": ["similar_to_past_severe"],
                }
            )

        suspected_code_paths = [
            f"services/{service}/{_slug_component(operation)}.py",
            *[
                f"repos/{repo_candidate}/{_slug_component(operation)}"
                for repo_candidate in packet["topology"]["repo_candidates"][:2]
            ],
        ]
        boundary = load_provider_boundary_config(self.provider_boundary_path).local_primary

        tool_notes = [
            "local_primary_smoke_result",
            f"local_primary_provider_mode={boundary.mode}",
            f"local_primary_current_smoke_model={boundary.smoke.model_name}",
            f"local_primary_future_real_adapter={boundary.real_adapter.adapter}",
            (
                "local_primary_future_real_adapter_enabled_env="
                f"{boundary.real_adapter.enabled_env}"
            ),
        ]
        unknowns = [
            "bounded tool wrappers are not connected yet; live follow-up queries remain pending",
        ]
        tool_calls_used = 0
        live_trace_ids: list[str] = []
        live_log_refs: list[str] = []
        live_error_rate: float | None = None
        if self.tools is not None:
            tool_session = self.tools.clone_for_investigation()
            repo_hits = tool_session.repo_search(suspected_code_paths[0], limit=2)
            tool_notes.extend(
                [
                    "bounded_repo_search_used",
                    f"repo_search_hit_count={len(repo_hits)}",
                ]
            )
            unknowns = [
                "bounded local follow-up used repo_search only; live metric/log follow-up remains pending",
            ]

            if _is_live_evidence_request(request):
                prometheus_endpoint, prometheus_query = (
                    _parse_promql_ref(request.prometheus_query_refs[0]) if request.prometheus_query_refs else (None, None)
                )
                live_error_rate = (
                    tool_session.prometheus_query_scalar(prometheus_query, endpoint_name=prometheus_endpoint)
                    if prometheus_query
                    else None
                )
                live_logs = tool_session.signoz_search_logs(service, limit=2)
                live_traces = tool_session.signoz_search_traces(service, limit=2)
                live_operations = tool_session.get_signoz_top_operations(service, time_range="30m")
                if live_logs:
                    primary_cause = str(live_logs[0].get("body") or primary_cause)
                if live_operations:
                    operation_name = str(live_operations[0].get("name") or operation)
                    hypotheses[0]["hypothesis"] = f"{primary_cause} is driving the {service} regression on {operation_name}"
                live_trace_ids = [
                    str(row.get("traceId") or row.get("trace_id") or row.get("id"))
                    for row in live_traces
                    if row.get("traceId") or row.get("trace_id") or row.get("id")
                ]
                live_log_refs = [
                    f"signoz-mcp://log-row/{row.get('id') or index}"
                    for index, row in enumerate(live_logs, start=1)
                ]
                tool_notes.extend(
                    [
                        "live_prometheus_followup_used",
                        "live_signoz_logs_used",
                        "live_signoz_traces_used",
                        f"live_error_rate={live_error_rate if live_error_rate is not None else 'none'}",
                        f"live_log_rows={len(live_logs)}",
                        f"live_trace_rows={len(live_traces)}",
                    ]
                )
                unknowns = [
                    "bounded live follow-up used Prometheus + SigNoz + repo search; deeper confirmation may still be needed",
                ]
                if live_error_rate is not None:
                    hypotheses[0]["supporting_reason_codes"] = list(
                        dict.fromkeys([*reason_codes, "live_prometheus_followup"])
                    )
            tool_calls_used = tool_session.usage_snapshot().calls_used
        tool_notes.append(f"tool_calls_used={tool_calls_used}")

        return {
            "schema_version": "investigation-result.v1",
            "investigation_id": build_investigation_id(packet),
            "packet_id": str(packet["packet_id"]),
            "decision_id": str(decision["decision_id"]),
            "investigator_tier": "local_primary_investigator",
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "generated_at": datetime.fromisoformat(str(packet["created_at"]).replace("Z", "+00:00"))
            .astimezone(UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
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
                "severity_band": decision["severity_band"],
                "recommended_action": decision["recommended_action"],
                "confidence": confidence,
                "reason_codes": reason_codes,
                "suspected_primary_cause": primary_cause,
                "failure_chain_summary": (
                    f"{service} {operation} regressed after bounded first-pass analysis flagged "
                    f"{primary_cause}; current packet severity score is {severity_score}."
                    + (
                        f" live Prometheus follow-up kept error_rate at {live_error_rate}."
                        if live_error_rate is not None
                        else ""
                    )
                ),
            },
            "hypotheses": hypotheses,
            "analysis_updates": {
                "severity_band_changed": False,
                "recommended_action_changed": False,
                "fallback_invocation_was_correct": None,
                "notes": tool_notes,
            },
            "routing": {
                "owner_hint": packet["topology"]["owner"],
                "repo_candidates": list(packet["topology"]["repo_candidates"]),
                "suspected_code_paths": suspected_code_paths[:3],
                "escalation_target": packet["topology"]["owner"],
            },
            "evidence_refs": {
                "prometheus_ref_ids": list(request.prometheus_query_refs),
                "signoz_ref_ids": list(dict.fromkeys([*request.signoz_query_refs, *live_log_refs])),
                "trace_ids": list(dict.fromkeys([*request.sample_trace_ids, *live_trace_ids])),
                "code_refs": list(request.code_search_refs) or suspected_code_paths[:2],
            },
            "unknowns": unknowns,
        }

    def _investigate_signoz_first(self, request: InvestigationRequest) -> InvestigationResult:
        packet = request.packet
        decision = request.decision
        signoz = packet["signoz"]
        service = str(packet["service"])
        top_operation = signoz["top_slow_operations"][0]
        operation = str(top_operation.get("operation") or packet.get("operation") or service)
        top_template = signoz["top_error_templates"][0]
        alert_context = signoz.get("alert_context") or {}
        packet_trace_hints = _packet_trace_detail_hints(packet)
        primary_cause = str(top_template["template"])
        confidence_bonus = 0.18 + (0.12 if packet_trace_hints else 0.0) + (0.05 if request.sample_trace_ids else 0.0)
        confidence = round_score(min(1.0, float(decision["confidence"]) + confidence_bonus))
        reason_codes = decision["reason_codes"][:4]
        if not reason_codes:
            reason_codes = ["local_primary_smoke"]

        suspected_code_paths = [
            f"services/{service}/{_slug_component(operation)}.py",
            *[
                f"repos/{repo_candidate}/{_slug_component(operation)}"
                for repo_candidate in packet["topology"]["repo_candidates"][:2]
            ],
        ]
        boundary = load_provider_boundary_config(self.provider_boundary_path).local_primary

        tool_notes = [
            "local_primary_smoke_result",
            "packet_signoz_alert_context_used",
            f"local_primary_provider_mode={boundary.mode}",
            f"local_primary_current_smoke_model={boundary.smoke.model_name}",
            f"local_primary_future_real_adapter={boundary.real_adapter.adapter}",
            (
                "local_primary_future_real_adapter_enabled_env="
                f"{boundary.real_adapter.enabled_env}"
            ),
        ]
        if packet_trace_hints:
            tool_notes.append("packet_trace_detail_hints_used")

        live_trace_ids = list(request.sample_trace_ids)
        live_log_refs = list(request.sample_log_refs)
        live_error_rate: float | None = None
        primary_hint = packet_trace_hints[0] if packet_trace_hints else None
        if primary_hint is not None:
            target_summary = _trace_hint_summary(primary_hint)
            base_hypothesis = f"{target_summary} is driving the {service} regression on {operation}"
        else:
            base_hypothesis = f"SigNoz alert context indicates {primary_cause} is driving {service} on {operation}"

        hypotheses = [
            {
                "rank": 1,
                "hypothesis": base_hypothesis,
                "confidence": round_score(min(0.95, confidence + 0.06)),
                "supporting_reason_codes": list(dict.fromkeys([*reason_codes, "signoz_primary_evidence"])),
            }
        ]
        if request.retrieval_packet_ids:
            hypotheses.append(
                {
                    "rank": len(hypotheses) + 1,
                    "hypothesis": f"retrieval history suggests the current {service} issue resembles prior severe incidents",
                    "confidence": round_score(max(0.35, confidence - 0.22)),
                    "supporting_reason_codes": ["similar_to_past_severe"],
                }
            )

        unknowns = [
            "bounded Signoz-first follow-up used packet-carried alert context and trace hints; deeper dependency confirmation may still be needed",
        ]
        tool_calls_used = 0
        if self.tools is not None:
            tool_session = self.tools.clone_for_investigation()
            trace_ids_for_followup = list(dict.fromkeys(request.sample_trace_ids[:2]))
            live_trace_logs: list[dict[str, object]] = []
            if trace_ids_for_followup:
                trace_detail_used = False
                for trace_id in trace_ids_for_followup:
                    try:
                        tool_session.get_signoz_trace_details(trace_id, time_range="30m")
                    except Exception:
                        continue
                    trace_detail_used = True
                if trace_detail_used:
                    tool_notes.append("live_signoz_trace_details_used")
                for trace_id in trace_ids_for_followup:
                    try:
                        trace_logs = tool_session.signoz_search_logs_by_trace_id(trace_id, time_range="30m", limit=2)
                    except Exception:
                        continue
                    if trace_logs and not live_trace_logs:
                        live_trace_logs = trace_logs
                    if trace_logs:
                        live_log_refs.extend(
                            [
                                f"signoz-mcp://log-row/{row.get('id') or index}"
                                for index, row in enumerate(trace_logs, start=1)
                            ]
                        )
                if live_trace_logs:
                    tool_notes.append("live_signoz_trace_logs_used")
                    primary_cause = str(live_trace_logs[0].get("body") or primary_cause)
            live_operations = tool_session.get_signoz_top_operations(service, time_range="30m")
            tool_notes.append("live_signoz_top_operations_used")
            repo_hits = tool_session.repo_search(suspected_code_paths[0], limit=2)
            tool_notes.extend(["bounded_repo_search_used", f"repo_search_hit_count={len(repo_hits)}"])

            if request.prometheus_query_refs:
                prometheus_endpoint, prometheus_query = _parse_promql_ref(request.prometheus_query_refs[0])
                if prometheus_query:
                    try:
                        live_error_rate = tool_session.prometheus_query_scalar(
                            prometheus_query,
                            endpoint_name=prometheus_endpoint,
                        )
                    except Exception:
                        live_error_rate = None
                    tool_notes.append("live_prometheus_corroboration_used")
                    tool_notes.append(
                        f"live_prometheus_error_rate={live_error_rate if live_error_rate is not None else 'none'}"
                    )

            if live_operations:
                operation = str(live_operations[0].get("name") or operation)
            if primary_hint is not None:
                target_summary = _trace_hint_summary(primary_hint)
                hypotheses[0]["hypothesis"] = f"{target_summary} is driving the {service} regression on {operation}"
            else:
                hypotheses[0]["hypothesis"] = f"SigNoz alert context indicates {primary_cause} is driving {service} on {operation}"
            hypotheses[0]["supporting_reason_codes"] = list(
                dict.fromkeys([*reason_codes, "signoz_primary_evidence"])
            )
            unknowns = [
                "bounded Signoz-first follow-up used alert context, trace details, trace-log correlation, and repo search; Prometheus remained corroboration only",
            ]
            tool_calls_used = tool_session.usage_snapshot().calls_used
        tool_notes.append(f"tool_calls_used={tool_calls_used}")

        failure_chain = (
            f"SigNoz alert {alert_context.get('rule_id') or 'unknown'} fired for {service} {operation}; "
            f"top operation p95 is {top_operation.get('p95_ms')} ms; primary symptom is {primary_cause}."
        )
        if primary_hint is not None:
            failure_chain += f" Trace detail points to {_trace_hint_summary(primary_hint)}."
        if live_error_rate is not None:
            failure_chain += f" Prometheus corroboration error_rate={live_error_rate}."

        return {
            "schema_version": "investigation-result.v1",
            "investigation_id": build_investigation_id(packet),
            "packet_id": str(packet["packet_id"]),
            "decision_id": str(decision["decision_id"]),
            "investigator_tier": "local_primary_investigator",
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "generated_at": datetime.fromisoformat(str(packet["created_at"]).replace("Z", "+00:00"))
            .astimezone(UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
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
                "severity_band": decision["severity_band"],
                "recommended_action": decision["recommended_action"],
                "confidence": confidence,
                "reason_codes": reason_codes,
                "suspected_primary_cause": primary_cause,
                "failure_chain_summary": failure_chain,
            },
            "hypotheses": hypotheses,
            "analysis_updates": {
                "severity_band_changed": False,
                "recommended_action_changed": False,
                "fallback_invocation_was_correct": None,
                "notes": tool_notes,
            },
            "routing": {
                "owner_hint": packet["topology"]["owner"],
                "repo_candidates": list(packet["topology"]["repo_candidates"]),
                "suspected_code_paths": suspected_code_paths[:3],
                "escalation_target": packet["topology"]["owner"],
            },
            "evidence_refs": {
                "prometheus_ref_ids": list(request.prometheus_query_refs),
                "signoz_ref_ids": list(dict.fromkeys([*request.signoz_query_refs, *live_log_refs])),
                "trace_ids": list(dict.fromkeys(live_trace_ids)),
                "code_refs": list(request.code_search_refs) or suspected_code_paths[:2],
            },
            "unknowns": unknowns,
        }


__all__ = [
    "LocalPrimaryAbnormalPathDecision",
    "LocalPrimaryInvestigator",
    "LocalPrimaryPrewarmSource",
    "LocalPrimaryResidentLifecycle",
    "LocalPrimaryResidentResolution",
    "LocalPrimaryRuntimeContext",
    "RealAdapterProviderProtocol",
    "build_investigation_id",
    "build_real_local_primary_provider",
    "decide_local_primary_abnormal_path",
    "local_primary_abnormal_path_payload",
    "local_primary_resident_lifecycle_payload",
    "prewarm_local_primary_resident_service",
    "reset_local_primary_resident_service",
]
