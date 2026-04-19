"""Markdown alert report builder for warning-agent packet-first baseline."""

from __future__ import annotations

from typing import Any

import yaml

from app.reports.contracts import BODY_SECTION_ORDER, AlertReportFrontmatter


def _inline_list(values: list[str]) -> str:
    if not values:
        return "none"
    return ", ".join(f"`{value}`" for value in values)


def _is_signoz_first_packet(packet: dict[str, Any]) -> bool:
    return packet.get("candidate_source") == "signoz_alert" or bool(packet["signoz"].get("alert_context"))


def build_alert_report_frontmatter(
    packet: dict[str, Any],
    decision: dict[str, Any],
    investigation: dict[str, Any] | None = None,
) -> AlertReportFrontmatter:
    summary = investigation["summary"] if investigation else None
    routing = investigation["routing"] if investigation else None
    investigation_stage = "none"
    if investigation:
        investigation_stage = (
            "cloud_fallback"
            if investigation["investigator_tier"] == "cloud_fallback_investigator"
            else "local_primary"
        )
    return {
        "schema_version": "alert-report.v1",
        "report_id": "rpt_" + packet["packet_id"][4:],
        "packet_id": packet["packet_id"],
        "decision_id": decision["decision_id"],
        "generated_at": investigation["generated_at"] if investigation else packet["created_at"],
        "severity_band": summary["severity_band"] if summary else decision["severity_band"],
        "delivery_class": summary["recommended_action"] if summary else decision["recommended_action"],
        "investigation_stage": investigation_stage,
        "service": packet["service"],
        "operation": packet["operation"],
        "owner": routing["owner_hint"] if routing else packet["topology"]["owner"],
        "repo_candidates": routing["repo_candidates"] if routing else packet["topology"]["repo_candidates"],
        "prometheus_ref_ids": packet["evidence_refs"]["prometheus_query_refs"],
        "signoz_ref_ids": packet["evidence_refs"]["signoz_query_refs"],
    }


def _legacy_sections(
    packet: dict[str, Any],
    decision: dict[str, Any],
    investigation: dict[str, Any] | None,
    frontmatter: AlertReportFrontmatter,
) -> list[str]:
    summary = investigation["summary"] if investigation else None
    routing = investigation["routing"] if investigation else None
    evidence_refs = investigation["evidence_refs"] if investigation else None
    confidence = summary["confidence"] if summary else decision["confidence"]
    severity_band = frontmatter["severity_band"]
    delivery_class = frontmatter["delivery_class"]
    investigation_trigger_reasons = decision["investigation_trigger_reasons"] or ["none"]
    code_refs = evidence_refs["code_refs"] if evidence_refs else []
    hypotheses = investigation["hypotheses"] if investigation else []
    top_hypothesis = hypotheses[0]["hypothesis"] if hypotheses else "none"
    unknowns = investigation["unknowns"] if investigation else ["none"]
    next_checks = unknowns if unknowns != ["none"] else ["none"]
    escalation_target = routing["escalation_target"] if routing else packet["topology"]["owner"]

    return [
        "## Executive Summary\n"
        f"- service: `{packet['service']}`\n"
        f"- operation: `{packet['operation']}`\n"
        f"- window: `{packet['window']['start_ts']} -> {packet['window']['end_ts']}`\n"
        f"- severity band: `{severity_band}`\n"
        f"- confidence: `{confidence}`\n"
        f"- delivery class: `{delivery_class}`",
        "## Why This Alert Exists\n"
        f"- local reason codes: {_inline_list(decision['reason_codes'])}\n"
        f"- local summary: `novelty={decision['novelty_score']} confidence={decision['confidence']}`\n"
        f"- investigation trigger reasons: {_inline_list(investigation_trigger_reasons)}",
        "## Metric Signals\n"
        f"- firing alerts: {_inline_list(packet['prometheus']['alerts_firing'])}\n"
        f"- error rate delta: `{packet['prometheus']['error_rate_delta']}`\n"
        f"- p95 delta ms: `{packet['prometheus']['latency_p95_delta']}`\n"
        f"- qps delta: `{packet['prometheus']['qps_delta']}`\n"
        f"- saturation: `{packet['prometheus']['saturation']}`",
        "## Logs And Traces\n"
        f"- top template: `{packet['signoz']['top_error_templates'][0]['template']}` count=`{packet['signoz']['top_error_templates'][0]['count']}` novelty=`{packet['signoz']['top_error_templates'][0]['novelty_score']}`\n"
        f"- trace error ratio: `{packet['signoz']['trace_error_ratio']}`\n"
        f"- top slow op: `{packet['signoz']['top_slow_operations'][0]['operation']}` p95=`{packet['signoz']['top_slow_operations'][0]['p95_ms']}`",
        "## Investigation\n"
        + (
            f"- suspected primary cause: `{summary['suspected_primary_cause']}`\n"
            f"- suspected failure chain: `{summary['failure_chain_summary']}`\n"
            f"- top hypothesis: `{top_hypothesis}`\n"
            f"- likely repo or module: {_inline_list(routing['repo_candidates'])}\n"
            f"- code refs: {_inline_list(code_refs)}"
            if investigation
            else "- not used"
        ),
        "## Impact And Routing\n"
        f"- blast radius: `{packet['topology']['blast_radius_score']}`\n"
        f"- owner: `{frontmatter['owner']}`\n"
        f"- repo candidates: {_inline_list(frontmatter['repo_candidates'])}",
        "## Recommended Action\n"
        f"- immediate action: `{delivery_class}`\n"
        f"- next checks: {_inline_list(next_checks)}\n"
        f"- escalation target: `{escalation_target}`",
        "## Evidence Refs\n"
        f"- Prometheus: {_inline_list(frontmatter['prometheus_ref_ids'])}\n"
        f"- SigNoz: {_inline_list(frontmatter['signoz_ref_ids'])}\n"
        f"- Code: {_inline_list(code_refs)}",
        "## Unknowns\n" + "\n".join(f"- {item}" for item in unknowns),
    ]


def _signoz_first_sections(
    packet: dict[str, Any],
    decision: dict[str, Any],
    investigation: dict[str, Any] | None,
    frontmatter: AlertReportFrontmatter,
) -> list[str]:
    summary = investigation["summary"] if investigation else None
    routing = investigation["routing"] if investigation else None
    evidence_refs = investigation["evidence_refs"] if investigation else None
    confidence = summary["confidence"] if summary else decision["confidence"]
    severity_band = frontmatter["severity_band"]
    delivery_class = frontmatter["delivery_class"]
    investigation_trigger_reasons = decision["investigation_trigger_reasons"] or ["none"]
    code_refs = evidence_refs["code_refs"] if evidence_refs else []
    trace_ids = evidence_refs["trace_ids"] if evidence_refs else packet["signoz"]["sample_trace_ids"]
    hypotheses = investigation["hypotheses"] if investigation else []
    top_hypothesis = hypotheses[0]["hypothesis"] if hypotheses else "none"
    unknowns = investigation["unknowns"] if investigation else ["none"]
    next_checks = unknowns if unknowns != ["none"] else ["none"]
    escalation_target = routing["escalation_target"] if routing else packet["topology"]["owner"]
    alert_context = packet["signoz"].get("alert_context") or {}
    trace_hints = packet["signoz"].get("trace_detail_hints") or []
    first_hint = trace_hints[0] if trace_hints else {}

    return [
        "## Executive Summary\n"
        f"- service: `{packet['service']}`\n"
        f"- operation: `{packet['operation']}`\n"
        f"- severity band: `{severity_band}`\n"
        f"- confidence: `{confidence}`\n"
        f"- delivery class: `{delivery_class}`\n"
        f"- SigNoz primary evidence: rule=`{alert_context.get('rule_id')}` trace_ids={_inline_list(trace_ids) if trace_ids else 'none'}",
        "## Why This Alert Exists\n"
        f"- SigNoz alert context: severity=`{alert_context.get('severity')}` eval_window=`{alert_context.get('eval_window')}`\n"
        f"- reason codes: {_inline_list(decision['reason_codes'])}\n"
        f"- investigation trigger reasons: {_inline_list(investigation_trigger_reasons)}",
        "## Metric Signals\n"
        "- Prometheus corroboration only\n"
        f"- error rate delta: `{packet['prometheus']['error_rate_delta']}`\n"
        f"- p95 delta ms: `{packet['prometheus']['latency_p95_delta']}`\n"
        f"- qps delta: `{packet['prometheus']['qps_delta']}`\n"
        f"- saturation: `{packet['prometheus']['saturation']}`",
        "## Logs And Traces\n"
        f"- top template: `{packet['signoz']['top_error_templates'][0]['template']}` count=`{packet['signoz']['top_error_templates'][0]['count']}` novelty=`{packet['signoz']['top_error_templates'][0]['novelty_score']}`\n"
        f"- trace error ratio: `{packet['signoz']['trace_error_ratio']}`\n"
        f"- top slow op: `{packet['signoz']['top_slow_operations'][0]['operation']}` p95=`{packet['signoz']['top_slow_operations'][0]['p95_ms']}`\n"
        f"- primary trace hint: `{first_hint.get('service_name') or first_hint.get('target') or 'none'}` status=`{first_hint.get('status_code') or 'none'}`",
        "## Investigation\n"
        + (
            f"- suspected primary cause: `{summary['suspected_primary_cause']}`\n"
            f"- suspected failure chain: `{summary['failure_chain_summary']}`\n"
            f"- top hypothesis: `{top_hypothesis}`\n"
            f"- Signoz primary refs: {_inline_list(frontmatter['signoz_ref_ids'])}\n"
            f"- code refs: {_inline_list(code_refs)}"
            if investigation
            else "- not used"
        ),
        "## Impact And Routing\n"
        f"- blast radius: `{packet['topology']['blast_radius_score']}`\n"
        f"- owner: `{frontmatter['owner']}`\n"
        f"- repo candidates: {_inline_list(frontmatter['repo_candidates'])}",
        "## Recommended Action\n"
        f"- immediate action: `{delivery_class}`\n"
        f"- next checks: {_inline_list(next_checks)}\n"
        f"- escalation target: `{escalation_target}`",
        "## Evidence Refs\n"
        f"- Prometheus corroboration refs: {_inline_list(frontmatter['prometheus_ref_ids'])}\n"
        f"- SigNoz primary refs: {_inline_list(frontmatter['signoz_ref_ids'])}\n"
        f"- Code: {_inline_list(code_refs)}",
        "## Unknowns\n" + "\n".join(f"- {item}" for item in unknowns),
    ]


def render_alert_report(
    packet: dict[str, Any],
    decision: dict[str, Any],
    investigation: dict[str, Any] | None = None,
) -> str:
    frontmatter = build_alert_report_frontmatter(packet, decision, investigation)
    frontmatter_yaml = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    sections = (
        _signoz_first_sections(packet, decision, investigation, frontmatter)
        if _is_signoz_first_packet(packet)
        else _legacy_sections(packet, decision, investigation, frontmatter)
    )

    headings = [section.splitlines()[0].removeprefix("## ") for section in sections]
    if headings != BODY_SECTION_ORDER:
        raise ValueError(f"report section order drifted: {headings}")

    return f"---\n{frontmatter_yaml}\n---\n\n" + "\n\n".join(sections) + "\n"
