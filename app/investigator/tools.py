"""Bounded investigator tool wrappers for local-first follow-up."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.collectors.prometheus import PrometheusCollector
from app.collectors.signoz import SignozCollector
from app.investigator.base import InvestigatorBudget
from app.investigator.router import load_investigator_routing_config


class ToolBudgetExceededError(RuntimeError):
    """Raised when an investigation exceeds its bounded tool budget."""


class SignozCollectorProtocol(Protocol):
    def list_services(self, *, time_range: str = "30m", limit: int = 10, offset: int = 0) -> dict[str, Any]:
        ...

    def get_service_top_operations(self, service: str, *, time_range: str = "30m") -> list[dict[str, Any]]:
        ...

    def search_logs(self, service: str, *, time_range: str = "30m", severity: str = "ERROR", limit: int = 5) -> list[dict[str, Any]]:
        ...

    def search_traces(self, service: str, *, time_range: str = "30m", error: str = "true", limit: int = 5) -> list[dict[str, Any]]:
        ...

    def get_trace_details(self, trace_id: str, *, time_range: str = "30m") -> dict[str, Any]:
        ...

    def search_logs_by_trace_id(self, trace_id: str, *, time_range: str = "30m", limit: int = 5) -> list[dict[str, Any]]:
        ...


class PrometheusCollectorProtocol(Protocol):
    def smoke_query_up(self, endpoint_name: str | None = None) -> dict[str, Any]:
        ...

    def instant_scalar_query(self, query: str, endpoint_name: str | None = None) -> float | None:
        ...


@dataclass(frozen=True)
class RepoSearchHit:
    path: str
    line_number: int
    line_text: str


@dataclass(frozen=True)
class ToolUsageSnapshot:
    calls_used: int
    calls_remaining: int


class BoundedInvestigatorTools:
    def __init__(
        self,
        *,
        budget: InvestigatorBudget,
        repo_root: Path = Path('.'),
        signoz_collector: SignozCollectorProtocol | None = None,
        prometheus_collector: PrometheusCollectorProtocol | None = None,
    ) -> None:
        self.budget = budget
        self.repo_root = Path(repo_root)
        self.signoz_collector = signoz_collector or SignozCollector()
        self.prometheus_collector = prometheus_collector or PrometheusCollector()
        self._calls_used = 0

    @classmethod
    def from_config(cls, *, repo_root: Path = Path('.')) -> "BoundedInvestigatorTools":
        config = load_investigator_routing_config(Path(repo_root) / 'configs' / 'escalation.yaml')
        return cls(budget=config.local_primary.budget, repo_root=repo_root)

    def clone_for_investigation(self) -> "BoundedInvestigatorTools":
        return BoundedInvestigatorTools(
            budget=self.budget,
            repo_root=self.repo_root,
            signoz_collector=self.signoz_collector,
            prometheus_collector=self.prometheus_collector,
        )

    def usage_snapshot(self) -> ToolUsageSnapshot:
        return ToolUsageSnapshot(
            calls_used=self._calls_used,
            calls_remaining=max(0, self.budget.max_tool_calls - self._calls_used),
        )

    def _consume_call(self) -> None:
        if self._calls_used >= self.budget.max_tool_calls:
            raise ToolBudgetExceededError("investigator tool call budget exhausted")
        self._calls_used += 1

    def list_signoz_services(self, *, time_range: str = '30m', limit: int = 10, offset: int = 0) -> dict[str, Any]:
        self._consume_call()
        capped_limit = min(limit, self.budget.max_retrieval_refs)
        return self.signoz_collector.list_services(time_range=time_range, limit=capped_limit, offset=offset)

    def get_signoz_top_operations(self, service: str, *, time_range: str = '30m') -> list[dict[str, Any]]:
        self._consume_call()
        operations = self.signoz_collector.get_service_top_operations(service, time_range=time_range)
        return operations[: self.budget.max_trace_refs]

    def prometheus_up(self, endpoint_name: str | None = None) -> dict[str, Any]:
        self._consume_call()
        return self.prometheus_collector.smoke_query_up(endpoint_name)

    def prometheus_query_scalar(self, query: str, *, endpoint_name: str | None = None) -> float | None:
        self._consume_call()
        return self.prometheus_collector.instant_scalar_query(query, endpoint_name)

    def signoz_search_logs(
        self,
        service: str,
        *,
        severity: str = 'ERROR',
        time_range: str = '30m',
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        self._consume_call()
        capped_limit = min(limit or self.budget.max_log_refs, self.budget.max_log_refs)
        return self.signoz_collector.search_logs(service, time_range=time_range, severity=severity, limit=capped_limit)

    def signoz_search_traces(
        self,
        service: str,
        *,
        error: str = 'true',
        time_range: str = '30m',
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        self._consume_call()
        capped_limit = min(limit or self.budget.max_trace_refs, self.budget.max_trace_refs)
        return self.signoz_collector.search_traces(service, time_range=time_range, error=error, limit=capped_limit)

    def get_signoz_trace_details(self, trace_id: str, *, time_range: str = '30m') -> dict[str, Any]:
        self._consume_call()
        return self.signoz_collector.get_trace_details(trace_id, time_range=time_range)

    def signoz_search_logs_by_trace_id(
        self,
        trace_id: str,
        *,
        time_range: str = '30m',
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        self._consume_call()
        capped_limit = min(limit or self.budget.max_log_refs, self.budget.max_log_refs)
        return self.signoz_collector.search_logs_by_trace_id(trace_id, time_range=time_range, limit=capped_limit)

    def repo_search(
        self,
        query: str,
        *,
        limit: int | None = None,
        extensions: tuple[str, ...] = ('.py', '.md', '.json', '.yaml'),
    ) -> list[RepoSearchHit]:
        self._consume_call()
        max_results = min(limit or self.budget.max_code_refs, self.budget.max_code_refs)
        results: list[RepoSearchHit] = []

        for path in sorted(self.repo_root.rglob('*')):
            if len(results) >= max_results:
                break
            if not path.is_file() or path.suffix not in extensions:
                continue
            try:
                lines = path.read_text(encoding='utf-8').splitlines()
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(lines, start=1):
                if query not in line:
                    continue
                results.append(
                    RepoSearchHit(
                        path=str(path.relative_to(self.repo_root)),
                        line_number=line_number,
                        line_text=line.strip(),
                    )
                )
                if len(results) >= max_results:
                    break

        return results
