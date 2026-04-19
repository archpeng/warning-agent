from __future__ import annotations

from pathlib import Path

from app.collectors.prometheus import DEFAULT_PROMETHEUS_ENDPOINTS, PrometheusCollector, load_prometheus_defaults


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_default_prometheus_endpoints_expose_primary_secondary_and_optional() -> None:
    names = [endpoint.name for endpoint in DEFAULT_PROMETHEUS_ENDPOINTS]

    assert names == ["primary", "secondary", "temporal_optional"]
    assert DEFAULT_PROMETHEUS_ENDPOINTS[2].enabled is False


def test_prometheus_defaults_load_from_collectors_config() -> None:
    endpoints, timeout_sec = load_prometheus_defaults(REPO_ROOT / "configs" / "collectors.yaml")

    assert [endpoint.name for endpoint in endpoints] == ["primary", "secondary", "temporal_optional"]
    assert endpoints[0].base_url == "http://192.168.33.16:9090"
    assert timeout_sec == 10.0



def test_collector_resolves_enabled_endpoint_by_default() -> None:
    collector = PrometheusCollector()

    endpoint = collector._resolve_endpoint()

    assert endpoint.name == "primary"
    assert endpoint.base_url == "http://192.168.33.16:9090"


def test_extract_scalar_value_supports_scalar_result_type() -> None:
    payload = {
        "status": "success",
        "data": {
            "resultType": "scalar",
            "result": [1713513600, "0.81"],
        },
    }

    assert PrometheusCollector._extract_scalar_value(payload) == 0.81


def test_extract_scalar_value_supports_vector_result_type_and_empty_results() -> None:
    payload = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {"service": "checkout"},
                    "value": [1713513600, "122"],
                }
            ],
        },
    }
    empty_payload = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [],
        },
    }

    assert PrometheusCollector._extract_scalar_value(payload) == 122.0
    assert PrometheusCollector._extract_scalar_value(empty_payload) is None
