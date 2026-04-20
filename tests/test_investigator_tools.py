from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from app.investigator.router import load_investigator_routing_config
from app.investigator.tools import BoundedInvestigatorTools, ToolBudgetExceededError


REPO_ROOT = Path(__file__).resolve().parents[1]


class FakeSignozCollector:
    def __init__(self) -> None:
        self.list_calls: list[tuple[str, int, int]] = []
        self.operation_calls: list[tuple[str, str]] = []
        self.log_calls: list[tuple[str, str, str, int]] = []
        self.trace_calls: list[tuple[str, str, str, int]] = []
        self.trace_detail_calls: list[tuple[str, str]] = []
        self.trace_log_calls: list[tuple[str, str, int]] = []

    def list_services(self, *, time_range: str = "30m", limit: int = 10, offset: int = 0) -> dict:
        self.list_calls.append((time_range, limit, offset))
        return {
            "services": [{"serviceName": f"service-{index}"} for index in range(limit)],
            "pagination": {"limit": limit, "offset": offset},
        }

    def get_service_top_operations(self, service: str, *, time_range: str = "30m") -> list[dict]:
        self.operation_calls.append((service, time_range))
        return [
            {"name": f"{service}-operation-{index}", "count": index + 1}
            for index in range(12)
        ]

    def search_logs(self, service: str, *, time_range: str = "30m", severity: str = "ERROR", limit: int = 5) -> list[dict]:
        self.log_calls.append((service, time_range, severity, limit))
        return [{"id": f"log-{index}", "body": f"{service}-log-{index}"} for index in range(limit)]

    def search_traces(self, service: str, *, time_range: str = "30m", error: str = "true", limit: int = 5) -> list[dict]:
        self.trace_calls.append((service, time_range, error, limit))
        return [{"traceId": f"trace-{index}"} for index in range(limit)]

    def get_trace_details(self, trace_id: str, *, time_range: str = "30m") -> dict:
        self.trace_detail_calls.append((trace_id, time_range))
        return {"traceId": trace_id, "spans": [{"name": "POST /api/pay"}]}

    def search_logs_by_trace_id(self, trace_id: str, *, time_range: str = "30m", limit: int = 5) -> list[dict]:
        self.trace_log_calls.append((trace_id, time_range, limit))
        return [{"id": f"log-{trace_id}", "body": f"trace-log-{trace_id}"} for _ in range(limit)]


class FakePrometheusCollector:
    def __init__(self) -> None:
        self.calls: list[str | None] = []
        self.scalar_calls: list[tuple[str, str | None]] = []

    def smoke_query_up(self, endpoint_name: str | None = None) -> dict:
        self.calls.append(endpoint_name)
        return {
            "endpoint_name": endpoint_name or "primary",
            "base_url": "http://prometheus.example",
            "query": "up",
            "result_type": "vector",
            "series_count": 4,
        }

    def instant_scalar_query(self, query: str, endpoint_name: str | None = None) -> float | None:
        self.scalar_calls.append((query, endpoint_name))
        return 0.21


def _budget():
    return load_investigator_routing_config(REPO_ROOT / "configs" / "escalation.yaml").local_primary.budget


def test_bounded_tools_clamp_signoz_service_limit() -> None:
    signoz = FakeSignozCollector()
    tools = BoundedInvestigatorTools(
        budget=_budget(),
        repo_root=REPO_ROOT,
        signoz_collector=signoz,
        prometheus_collector=FakePrometheusCollector(),
    )

    payload = tools.list_signoz_services(limit=99)

    assert signoz.list_calls == [("30m", _budget().max_retrieval_refs, 0)]
    assert len(payload["services"]) == _budget().max_retrieval_refs
    assert tools.usage_snapshot().calls_used == 1


def test_bounded_tools_cap_signoz_top_operations() -> None:
    signoz = FakeSignozCollector()
    tools = BoundedInvestigatorTools(
        budget=_budget(),
        repo_root=REPO_ROOT,
        signoz_collector=signoz,
        prometheus_collector=FakePrometheusCollector(),
    )

    operations = tools.get_signoz_top_operations("checkout")

    assert signoz.operation_calls == [("checkout", "30m")]
    assert len(operations) == _budget().max_trace_refs
    assert tools.usage_snapshot().calls_used == 1


def test_bounded_tools_wrap_prometheus_smoke_query() -> None:
    prometheus = FakePrometheusCollector()
    tools = BoundedInvestigatorTools(
        budget=_budget(),
        repo_root=REPO_ROOT,
        signoz_collector=FakeSignozCollector(),
        prometheus_collector=prometheus,
    )

    summary = tools.prometheus_up("secondary")

    assert prometheus.calls == ["secondary"]
    assert summary["series_count"] == 4
    assert tools.usage_snapshot().calls_used == 1


def test_bounded_tools_wrap_live_followup_queries_with_budget_caps() -> None:
    signoz = FakeSignozCollector()
    prometheus = FakePrometheusCollector()
    tools = BoundedInvestigatorTools(
        budget=_budget(),
        repo_root=REPO_ROOT,
        signoz_collector=signoz,
        prometheus_collector=prometheus,
    )

    value = tools.prometheus_query_scalar("checkout_error_rate", endpoint_name="primary")
    logs = tools.signoz_search_logs("checkout", limit=99)
    traces = tools.signoz_search_traces("checkout", limit=99)

    assert value == 0.21
    assert prometheus.scalar_calls == [("checkout_error_rate", "primary")]
    assert signoz.log_calls == [("checkout", "30m", "ERROR", _budget().max_log_refs)]
    assert signoz.trace_calls == [("checkout", "30m", "true", _budget().max_trace_refs)]
    assert len(logs) == _budget().max_log_refs
    assert len(traces) == _budget().max_trace_refs
    assert tools.usage_snapshot().calls_used == 3


def test_bounded_tools_repo_search_and_call_budget_are_capped(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "one.py").write_text("timeout\ntimeout\ntimeout\n", encoding="utf-8")
    (repo_root / "two.md").write_text("timeout\ntimeout\n", encoding="utf-8")

    budget = replace(_budget(), max_tool_calls=2, max_code_refs=2)
    tools = BoundedInvestigatorTools(
        budget=budget,
        repo_root=repo_root,
        signoz_collector=FakeSignozCollector(),
        prometheus_collector=FakePrometheusCollector(),
    )

    hits = tools.repo_search("timeout", limit=10)

    assert len(hits) == 2
    assert hits[0].path in {"one.py", "two.md"}

    tools.prometheus_up()
    with pytest.raises(ToolBudgetExceededError, match="budget exhausted"):
        tools.list_signoz_services()


def test_bounded_tools_wrap_signoz_trace_details_and_trace_logs() -> None:
    signoz = FakeSignozCollector()
    tools = BoundedInvestigatorTools(
        budget=_budget(),
        repo_root=REPO_ROOT,
        signoz_collector=signoz,
        prometheus_collector=FakePrometheusCollector(),
    )

    trace_details = tools.get_signoz_trace_details("trace-123")
    trace_logs = tools.signoz_search_logs_by_trace_id("trace-123", limit=99)

    assert trace_details == {"traceId": "trace-123", "spans": [{"name": "POST /api/pay"}]}
    assert len(trace_logs) == _budget().max_log_refs
    assert signoz.trace_detail_calls == [("trace-123", "30m")]
    assert signoz.trace_log_calls == [("trace-123", "30m", _budget().max_log_refs)]
    assert tools.usage_snapshot().calls_used == 2
