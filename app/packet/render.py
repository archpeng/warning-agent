"""Render packet and report artifacts into retrieval-friendly text surfaces."""

from __future__ import annotations

from typing import Any


def render_incident_packet(packet: dict[str, Any]) -> str:
    top_template = packet["signoz"]["top_error_templates"][0]["template"]
    top_slow_operation = packet["signoz"]["top_slow_operations"][0]["operation"]
    repo_candidates = ", ".join(packet["topology"]["repo_candidates"]) or "none"
    alerts_firing = ", ".join(packet["prometheus"]["alerts_firing"]) or "none"
    return "\n".join(
        [
            f"service: {packet['service']}",
            f"operation: {packet['operation']}",
            f"environment: {packet['environment']}",
            f"alerts_firing: {alerts_firing}",
            f"error_rate_delta: {packet['prometheus']['error_rate_delta']}",
            f"latency_p95_delta: {packet['prometheus']['latency_p95_delta']}",
            f"top_error_template: {top_template}",
            f"top_slow_operation: {top_slow_operation}",
            f"repo_candidates: {repo_candidates}",
        ]
    )


def render_markdown_report(report_markdown: str) -> str:
    return report_markdown.strip()
