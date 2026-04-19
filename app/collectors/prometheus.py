"""Deterministic Prometheus collector primitives for warning-agent."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, TypedDict

import httpx
import yaml


@dataclass(frozen=True)
class PrometheusEndpoint:
    name: str
    base_url: str
    enabled: bool = True


DEFAULT_PROMETHEUS_CONFIG_PATH: Final[Path] = Path(__file__).resolve().parents[2] / "configs" / "collectors.yaml"



def load_prometheus_defaults(
    config_path: str | Path = DEFAULT_PROMETHEUS_CONFIG_PATH,
) -> tuple[tuple[PrometheusEndpoint, ...], float]:
    payload = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    prometheus = payload.get("prometheus") or {}
    endpoints = tuple(
        PrometheusEndpoint(
            name=str(endpoint["name"]),
            base_url=str(endpoint["base_url"]),
            enabled=bool(endpoint.get("enabled", True)),
        )
        for endpoint in prometheus.get("endpoints", [])
    )
    return endpoints, float(prometheus.get("timeout_sec", 10.0))


DEFAULT_PROMETHEUS_ENDPOINTS, DEFAULT_PROMETHEUS_TIMEOUT_SEC = load_prometheus_defaults()


class PrometheusSmokeSummary(TypedDict):
    endpoint_name: str
    base_url: str
    query: str
    result_type: str
    series_count: int


class PrometheusCollector:
    def __init__(
        self,
        endpoints: tuple[PrometheusEndpoint, ...] = DEFAULT_PROMETHEUS_ENDPOINTS,
        timeout_sec: float = DEFAULT_PROMETHEUS_TIMEOUT_SEC,
    ) -> None:
        self.endpoints = endpoints
        self.timeout_sec = timeout_sec

    def _resolve_endpoint(self, endpoint_name: str | None = None) -> PrometheusEndpoint:
        if endpoint_name is None:
            for endpoint in self.endpoints:
                if endpoint.enabled:
                    return endpoint
            raise RuntimeError("no enabled Prometheus endpoints configured")

        for endpoint in self.endpoints:
            if endpoint.name == endpoint_name:
                if not endpoint.enabled:
                    raise ValueError(f"endpoint {endpoint_name} is disabled")
                return endpoint
        raise ValueError(f"unknown Prometheus endpoint: {endpoint_name}")

    def instant_query(self, query: str, endpoint_name: str | None = None) -> dict[str, Any]:
        endpoint = self._resolve_endpoint(endpoint_name)
        response = httpx.get(
            f"{endpoint.base_url}/api/v1/query",
            params={"query": query},
            timeout=self.timeout_sec,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            raise RuntimeError(f"Prometheus query failed: {payload}")
        return payload

    @staticmethod
    def _extract_scalar_value(payload: dict[str, Any]) -> float | None:
        data = payload.get("data") or {}
        result_type = data.get("resultType")
        result = data.get("result")

        if result_type == "scalar":
            if not isinstance(result, list) or len(result) < 2:
                return None
            return float(result[1])

        if result_type == "vector":
            if not isinstance(result, list) or not result:
                return None
            first = result[0]
            if not isinstance(first, dict):
                return None
            value = first.get("value")
            if not isinstance(value, list) or len(value) < 2:
                return None
            return float(value[1])

        return None

    def instant_scalar_query(self, query: str, endpoint_name: str | None = None) -> float | None:
        return self._extract_scalar_value(self.instant_query(query, endpoint_name))

    def smoke_query_up(self, endpoint_name: str | None = None) -> PrometheusSmokeSummary:
        endpoint = self._resolve_endpoint(endpoint_name)
        payload = self.instant_query("up", endpoint.name)
        data = payload["data"]
        result = data.get("result", [])
        return {
            "endpoint_name": endpoint.name,
            "base_url": endpoint.base_url,
            "query": "up",
            "result_type": data.get("resultType", "unknown"),
            "series_count": len(result),
        }
