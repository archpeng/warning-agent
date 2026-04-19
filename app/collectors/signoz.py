"""Deterministic SigNoz MCP-backed collector primitives for warning-agent."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import httpx
import yaml


@dataclass(frozen=True)
class SignozMCPSettings:
    base_url: str
    protocol_version: str
    client_name: str
    client_version: str


DEFAULT_SIGNOZ_CONFIG_PATH: Final[Path] = Path(__file__).resolve().parents[2] / "configs" / "collectors.yaml"



def load_signoz_defaults(config_path: str | Path = DEFAULT_SIGNOZ_CONFIG_PATH) -> tuple[SignozMCPSettings, float]:
    payload = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    signoz = payload.get("signoz") or {}
    required = ["base_url", "protocol_version", "client_name", "client_version"]
    missing = [key for key in required if key not in signoz]
    if missing:
        raise ValueError(f"missing SigNoz config fields: {', '.join(missing)}")
    return (
        SignozMCPSettings(
            base_url=str(signoz["base_url"]),
            protocol_version=str(signoz["protocol_version"]),
            client_name=str(signoz["client_name"]),
            client_version=str(signoz["client_version"]),
        ),
        float(signoz.get("timeout_sec", 20.0)),
    )


DEFAULT_SIGNOZ_SETTINGS, DEFAULT_SIGNOZ_TIMEOUT_SEC = load_signoz_defaults()


class SignozCollector:
    def __init__(
        self,
        settings: SignozMCPSettings = DEFAULT_SIGNOZ_SETTINGS,
        timeout_sec: float = DEFAULT_SIGNOZ_TIMEOUT_SEC,
    ) -> None:
        self.settings = settings
        self.timeout_sec = timeout_sec
        self._session_id: str | None = None
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout_sec)

    def _initialize_session(self) -> str:
        if self._session_id is not None:
            return self._session_id

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": self.settings.protocol_version,
                "capabilities": {},
                "clientInfo": {
                    "name": self.settings.client_name,
                    "version": self.settings.client_version,
                },
            },
        }
        with self._client() as client:
            response = client.post(self.settings.base_url, json=payload)
            response.raise_for_status()
            self._session_id = response.headers["Mcp-Session-Id"]
            client.post(
                self.settings.base_url,
                json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
                headers={"Mcp-Session-Id": self._session_id},
            ).raise_for_status()
        return self._session_id

    @staticmethod
    def _extract_text_content(response_payload: dict[str, Any]) -> str:
        content = response_payload.get("result", {}).get("content", [])
        if not content:
            raise RuntimeError(f"SigNoz MCP response missing content: {response_payload}")
        text = content[0].get("text")
        if not text:
            raise RuntimeError(f"SigNoz MCP content missing text payload: {response_payload}")
        return text

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any] | list[Any]:
        session_id = self._initialize_session()
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        with self._client() as client:
            response = client.post(
                self.settings.base_url,
                json=payload,
                headers={"Mcp-Session-Id": session_id},
            )
            response.raise_for_status()
            rpc_payload = response.json()
        return json.loads(self._extract_text_content(rpc_payload))

    @staticmethod
    def _extract_rows(payload: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]

        for key in ("data", "logs", "traces", "operations", "items", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]

        data = payload.get("data")
        if isinstance(data, dict):
            nested = data.get("data")
            if isinstance(nested, dict):
                results = nested.get("results")
                if isinstance(results, list):
                    rows: list[dict[str, Any]] = []
                    for result in results:
                        if not isinstance(result, dict):
                            continue
                        result_rows = result.get("rows")
                        if not isinstance(result_rows, list):
                            continue
                        for row in result_rows:
                            if not isinstance(row, dict):
                                continue
                            inner = row.get("data")
                            rows.append(inner if isinstance(inner, dict) else row)
                    if rows:
                        return rows

        return []

    def list_services(self, *, time_range: str = "30m", limit: int = 10, offset: int = 0) -> dict[str, Any]:
        return self.call_tool(
            "signoz_list_services",
            {"timeRange": time_range, "limit": str(limit), "offset": str(offset)},
        )

    def get_service_top_operations(self, service: str, *, time_range: str = "30m") -> list[dict[str, Any]]:
        payload = self.call_tool(
            "signoz_get_service_top_operations",
            {"service": service, "timeRange": time_range},
        )
        return self._extract_rows(payload)

    def search_logs(
        self,
        service: str,
        *,
        time_range: str = "30m",
        severity: str = "ERROR",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        payload = self.call_tool(
            "signoz_search_logs",
            {"service": service, "severity": severity, "timeRange": time_range, "limit": str(limit)},
        )
        return self._extract_rows(payload)

    def search_traces(
        self,
        service: str,
        *,
        time_range: str = "30m",
        error: str = "true",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        payload = self.call_tool(
            "signoz_search_traces",
            {"service": service, "error": error, "timeRange": time_range, "limit": str(limit)},
        )
        return self._extract_rows(payload)

    def get_trace_details(
        self,
        trace_id: str,
        *,
        time_range: str = "30m",
        include_spans: bool = True,
    ) -> dict[str, Any]:
        payload = self.call_tool(
            "signoz_get_trace_details",
            {
                "traceId": trace_id,
                "timeRange": time_range,
                "includeSpans": "true" if include_spans else "false",
            },
        )
        if isinstance(payload, dict):
            return payload
        raise RuntimeError(f"unexpected SigNoz trace detail payload: {payload!r}")

    def search_logs_by_trace_id(
        self,
        trace_id: str,
        *,
        time_range: str = "30m",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        payload = self.call_tool(
            "signoz_search_logs",
            {
                "query": f"trace_id = '{trace_id}' OR traceId = '{trace_id}' OR traceID = '{trace_id}'",
                "timeRange": time_range,
                "limit": str(limit),
            },
        )
        return self._extract_rows(payload)
