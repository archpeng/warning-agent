from __future__ import annotations

from pathlib import Path

from app.collectors.signoz import DEFAULT_SIGNOZ_SETTINGS, SignozCollector, load_signoz_defaults


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_signoz_settings_default_to_local_mcp() -> None:
    assert DEFAULT_SIGNOZ_SETTINGS.base_url == "http://127.0.0.1:3104/mcp"
    assert DEFAULT_SIGNOZ_SETTINGS.client_name == "warning-agent"



def test_signoz_defaults_load_from_collectors_config() -> None:
    settings, timeout_sec = load_signoz_defaults(REPO_ROOT / "configs" / "collectors.yaml")

    assert settings.base_url == "http://127.0.0.1:3104/mcp"
    assert settings.protocol_version == "2025-03-26"
    assert timeout_sec == 20.0


def test_extract_text_content_reads_first_text_block() -> None:
    payload = {
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": '{"data": [{"serviceName": "checkout"}], "pagination": {"hasMore": false}}',
                }
            ]
        }
    }

    assert (
        SignozCollector._extract_text_content(payload)
        == '{"data": [{"serviceName": "checkout"}], "pagination": {"hasMore": false}}'
    )


def test_extract_rows_supports_common_payload_shapes() -> None:
    assert SignozCollector._extract_rows({"data": [{"serviceName": "checkout"}]}) == [{"serviceName": "checkout"}]
    assert SignozCollector._extract_rows({"logs": [{"body": "timeout"}]}) == [{"body": "timeout"}]
    assert SignozCollector._extract_rows([{"traceId": "abc"}]) == [{"traceId": "abc"}]


def test_extract_rows_supports_raw_search_result_payloads() -> None:
    payload = {
        "status": "success",
        "data": {
            "type": "raw",
            "data": {
                "results": [
                    {
                        "queryName": "A",
                        "rows": [
                            {"data": {"traceID": "trace-1", "responseStatusCode": "503"}},
                            {"data": {"trace_id": "trace-2", "responseStatusCode": "504"}},
                        ],
                    }
                ]
            },
        },
    }

    assert SignozCollector._extract_rows(payload) == [
        {"traceID": "trace-1", "responseStatusCode": "503"},
        {"trace_id": "trace-2", "responseStatusCode": "504"},
    ]


def test_search_wrappers_call_expected_tools(monkeypatch) -> None:
    collector = SignozCollector()
    calls: list[tuple[str, dict]] = []

    def fake_call_tool(tool_name: str, arguments: dict):
        calls.append((tool_name, arguments))
        if tool_name == "signoz_search_logs":
            return {"logs": [{"body": "db timeout"}]}
        if tool_name == "signoz_search_traces":
            return [{"traceId": "trace-1"}]
        raise AssertionError(f"unexpected tool: {tool_name}")

    monkeypatch.setattr(collector, "call_tool", fake_call_tool)

    logs = collector.search_logs("checkout", severity="ERROR", limit=3)
    traces = collector.search_traces("checkout", error="true", limit=2)

    assert logs == [{"body": "db timeout"}]
    assert traces == [{"traceId": "trace-1"}]
    assert calls == [
        (
            "signoz_search_logs",
            {"service": "checkout", "severity": "ERROR", "timeRange": "30m", "limit": "3"},
        ),
        (
            "signoz_search_traces",
            {"service": "checkout", "error": "true", "timeRange": "30m", "limit": "2"},
        ),
    ]


def test_trace_detail_and_trace_log_wrappers_call_expected_tools(monkeypatch) -> None:
    collector = SignozCollector()
    calls: list[tuple[str, dict]] = []

    def fake_call_tool(tool_name: str, arguments: dict):
        calls.append((tool_name, arguments))
        if tool_name == "signoz_get_trace_details":
            return {"traceId": "trace-1", "spans": [{"name": "POST /api/pay"}]}
        if tool_name == "signoz_search_logs":
            return {"logs": [{"id": "log-1", "body": "trace-specific timeout"}]}
        raise AssertionError(f"unexpected tool: {tool_name}")

    monkeypatch.setattr(collector, "call_tool", fake_call_tool)

    trace_details = collector.get_trace_details("trace-1", time_range="15m")
    trace_logs = collector.search_logs_by_trace_id("trace-1", time_range="15m", limit=4)

    assert trace_details == {"traceId": "trace-1", "spans": [{"name": "POST /api/pay"}]}
    assert trace_logs == [{"id": "log-1", "body": "trace-specific timeout"}]
    assert calls == [
        (
            "signoz_get_trace_details",
            {"traceId": "trace-1", "timeRange": "15m", "includeSpans": "true"},
        ),
        (
            "signoz_search_logs",
            {
                "query": "trace_id = 'trace-1' OR traceId = 'trace-1' OR traceID = 'trace-1'",
                "timeRange": "15m",
                "limit": "4",
            },
        ),
    ]
