"""Bounded live evidence bundle assembly for warning-agent packets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Final
from urllib.parse import quote

import yaml

from app.collectors.prometheus import PrometheusCollector
from app.collectors.signoz import SignozCollector

if TYPE_CHECKING:
    from app.receiver.alertmanager_webhook import NormalizedAlertGroup

_CONFIG_DEFAULT_PATH: Final = Path("configs/evidence.yaml")
_SERVICES_CONFIG_PATH: Final = Path("configs/services.yaml")


@dataclass(frozen=True)
class EvidenceDefaults:
    window_sec: int
    prometheus_endpoint: str | None
    signoz_time_range: str
    signoz_logs_limit: int
    signoz_traces_limit: int
    signoz_top_operations_limit: int
    signoz_trace_details_limit: int
    signoz_trace_logs_limit: int
    fallback_novelty_score: float
    fallback_error_template_count: int


@dataclass(frozen=True)
class EvidenceServiceConfig:
    prometheus_queries: dict[str, str]


@dataclass(frozen=True)
class EvidenceCollectionConfig:
    defaults: EvidenceDefaults
    services: dict[str, EvidenceServiceConfig]


@dataclass(frozen=True)
class ServiceProfile:
    canonical_name: str
    tier: str
    owner_hint: str | None
    repo_hints: list[str]
    operation_allowlist: list[str]
    upstream_count: int
    downstream_count: int
    blast_radius_score: float


def load_evidence_collection_config(
    config_path: str | Path = _CONFIG_DEFAULT_PATH,
) -> EvidenceCollectionConfig:
    with Path(config_path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError("evidence config must be a mapping")

    defaults = payload["defaults"]
    services_payload = payload.get("services", {})
    services = {
        str(service): EvidenceServiceConfig(prometheus_queries=dict(service_payload.get("prometheus_queries", {})))
        for service, service_payload in services_payload.items()
    }
    return EvidenceCollectionConfig(
        defaults=EvidenceDefaults(
            window_sec=int(defaults["window_sec"]),
            prometheus_endpoint=(
                str(defaults["prometheus_endpoint"]) if defaults.get("prometheus_endpoint") is not None else None
            ),
            signoz_time_range=str(defaults["signoz_time_range"]),
            signoz_logs_limit=int(defaults["signoz_logs_limit"]),
            signoz_traces_limit=int(defaults["signoz_traces_limit"]),
            signoz_top_operations_limit=int(defaults["signoz_top_operations_limit"]),
            signoz_trace_details_limit=int(defaults.get("signoz_trace_details_limit", 2)),
            signoz_trace_logs_limit=int(defaults.get("signoz_trace_logs_limit", defaults["signoz_logs_limit"])),
            fallback_novelty_score=float(defaults["fallback_novelty_score"]),
            fallback_error_template_count=int(defaults["fallback_error_template_count"]),
        ),
        services=services,
    )


def load_service_profile(
    service: str,
    *,
    config_path: str | Path = _SERVICES_CONFIG_PATH,
) -> ServiceProfile:
    with Path(config_path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError("services config must be a mapping")
    services = payload.get("services", {})
    service_payload = services.get(service) or services["default"]
    return ServiceProfile(
        canonical_name=str(service_payload["canonical_name"]),
        tier=str(service_payload["tier"]),
        owner_hint=service_payload.get("owner_hint"),
        repo_hints=list(service_payload.get("repo_hints", [])),
        operation_allowlist=list(service_payload.get("operation_allowlist", [])),
        upstream_count=int(service_payload.get("upstream_count", 0)),
        downstream_count=int(service_payload.get("downstream_count", 0)),
        blast_radius_score=float(service_payload.get("blast_radius_score", 0.3)),
    )


def _iso_utc(timestamp: str | None = None) -> str:
    if timestamp is not None:
        return timestamp
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_window(*, created_at: str, window_sec: int) -> dict[str, object]:
    end = datetime.fromisoformat(created_at.replace("Z", "+00:00")).astimezone(UTC).replace(microsecond=0)
    start = end - timedelta(seconds=window_sec)
    return {
        "start_ts": start.isoformat().replace("+00:00", "Z"),
        "end_ts": end.isoformat().replace("+00:00", "Z"),
        "duration_sec": window_sec,
    }


def _slug_alertname(value: str | None) -> str:
    if not value:
        return "unknown_alert"
    out = []
    for char in value:
        if char.isupper() and out:
            out.append("_")
        out.append(char.lower() if char.isalnum() else "_")
    return "".join(out).strip("_") or "unknown_alert"


def _service_queries(
    service: str,
    *,
    config: EvidenceCollectionConfig,
) -> dict[str, str]:
    if service in config.services:
        return config.services[service].prometheus_queries
    return config.services.get("default", EvidenceServiceConfig(prometheus_queries={})).prometheus_queries


def _promql_ref(field: str, *, query: str, endpoint_name: str | None) -> str:
    encoded = quote(query, safe="")
    endpoint = quote(endpoint_name or "", safe="")
    return f"promql://{field}?endpoint={endpoint}&query={encoded}"


def _signoz_ref(kind: str, **params: object) -> str:
    encoded_params = "&".join(
        f"{quote(str(key), safe='')}={quote(str(value), safe='')}"
        for key, value in params.items()
        if value is not None and str(value) != ""
    )
    return f"signoz-mcp://{kind}" + (f"?{encoded_params}" if encoded_params else "")


def _safe_prometheus_value(
    collector: PrometheusCollector,
    *,
    query: str,
    endpoint_name: str | None,
) -> float | None:
    try:
        return collector.instant_scalar_query(query, endpoint_name)
    except Exception:
        return None


def _safe_signoz_logs(
    collector: SignozCollector,
    *,
    service: str,
    time_range: str,
    limit: int,
) -> list[dict[str, object]]:
    try:
        return collector.search_logs(service, time_range=time_range, severity="ERROR", limit=limit)
    except Exception:
        return []


def _safe_signoz_traces(
    collector: SignozCollector,
    *,
    service: str,
    time_range: str,
    limit: int,
) -> list[dict[str, object]]:
    try:
        return collector.search_traces(service, time_range=time_range, error="true", limit=limit)
    except Exception:
        return []


def _safe_signoz_operations(
    collector: SignozCollector,
    *,
    service: str,
    time_range: str,
) -> list[dict[str, object]]:
    try:
        return collector.get_service_top_operations(service, time_range=time_range)
    except Exception:
        return []


def _safe_signoz_trace_details(
    collector: SignozCollector,
    *,
    trace_id: str,
    time_range: str,
) -> dict[str, object] | None:
    try:
        payload = collector.get_trace_details(trace_id, time_range=time_range)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _safe_signoz_trace_logs(
    collector: SignozCollector,
    *,
    trace_id: str,
    time_range: str,
    limit: int,
) -> list[dict[str, object]]:
    try:
        return collector.search_logs_by_trace_id(trace_id, time_range=time_range, limit=limit)
    except Exception:
        return []


def _top_error_templates(
    logs: list[dict[str, object]],
    *,
    normalized_alert: "NormalizedAlertGroup",
    fallback_novelty_score: float,
    fallback_error_template_count: int,
) -> list[dict[str, object]]:
    if logs:
        templates: list[dict[str, object]] = []
        for index, row in enumerate(logs[:1], start=1):
            body = str(
                row.get("body") or row.get("message") or row.get("text") or normalized_alert.get("alertname") or ""
            )
            templates.append(
                {
                    "template_id": str(row.get("id") or f"live_log_template_{index}"),
                    "template": body,
                    "count": int(row.get("count") or fallback_error_template_count),
                    "novelty_score": float(row.get("novelty_score") or fallback_novelty_score),
                }
            )
        return templates

    fallback_template = (
        normalized_alert["common_annotations"].get("summary")
        or normalized_alert.get("alertname")
        or normalized_alert.get("service")
        or "live evidence fallback"
    )
    return [
        {
            "template_id": "live_fallback_template",
            "template": fallback_template,
            "count": fallback_error_template_count,
            "novelty_score": fallback_novelty_score,
        }
    ]


def _duration_to_ms(row: dict[str, object]) -> float:
    if row.get("p95_ms") is not None:
        return float(row["p95_ms"])
    if row.get("p95Ms") is not None:
        return float(row["p95Ms"])
    if row.get("avgDurationMs") is not None:
        return float(row["avgDurationMs"])
    if row.get("duration_ms") is not None:
        return float(row["duration_ms"])
    if row.get("p95") is not None:
        return round(float(row["p95"]) / 1_000_000, 4)
    return 0.0


def _top_slow_operations(
    operations: list[dict[str, object]],
    *,
    normalized_alert: "NormalizedAlertGroup",
) -> list[dict[str, object]]:
    if not operations:
        return [
            {
                "operation": str(normalized_alert.get("operation") or normalized_alert.get("service") or "unknown"),
                "p95_ms": 0.0,
                "error_ratio": None,
            }
        ]
    rows: list[dict[str, object]] = []
    for row in operations[:1]:
        rows.append(
            {
                "operation": str(
                    row.get("name") or row.get("operation") or normalized_alert.get("operation") or "unknown"
                ),
                "p95_ms": _duration_to_ms(row),
                "error_ratio": (
                    float(row["error_ratio"])
                    if row.get("error_ratio") is not None
                    else (float(row["errorRate"]) if row.get("errorRate") is not None else None)
                ),
            }
        )
    return rows


def _trace_error_ratio(traces: list[dict[str, object]]) -> float | None:
    ratios = [
        float(row["error_ratio"])
        for row in traces
        if isinstance(row, dict) and row.get("error_ratio") is not None
    ]
    if ratios:
        return round(sum(ratios) / len(ratios), 2)
    if not traces:
        return None
    return 1.0


def _sample_trace_ids(traces: list[dict[str, object]], *, limit: int) -> list[str]:
    return list(
        dict.fromkeys(
            str(row.get("traceId") or row.get("trace_id") or row.get("traceID") or row.get("id"))
            for row in traces[:limit]
            if row.get("traceId") or row.get("trace_id") or row.get("traceID") or row.get("id")
        )
    )


def _string_value(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _span_attribute(span: dict[str, object], *keys: str) -> str | None:
    for key in keys:
        direct = _string_value(span.get(key))
        if direct is not None:
            return direct

    for collection_key in ("attributes", "attributeMap", "tags"):
        collection = span.get(collection_key)
        if isinstance(collection, dict):
            for key in keys:
                nested = _string_value(collection.get(key))
                if nested is not None:
                    return nested
        if isinstance(collection, list):
            for item in collection:
                if not isinstance(item, dict):
                    continue
                name = _string_value(item.get("key") or item.get("name"))
                if name not in keys:
                    continue
                nested = _string_value(item.get("value") or item.get("stringValue"))
                if nested is not None:
                    return nested
    return None


def _trace_id_from_payload(payload: dict[str, object], fallback_trace_id: str | None = None) -> str | None:
    return _string_value(
        payload.get("traceId") or payload.get("trace_id") or payload.get("traceID") or fallback_trace_id
    )


def _trace_spans(payload: dict[str, object]) -> list[dict[str, object]]:
    candidates: list[object] = [
        payload,
        payload.get("data"),
        payload.get("result"),
    ]
    data = payload.get("data")
    if isinstance(data, dict):
        candidates.append(data.get("data"))
        candidates.append(data.get("result"))
        nested = data.get("data")
        if isinstance(nested, dict):
            results = nested.get("results")
            if isinstance(results, list):
                spans: list[dict[str, object]] = []
                for result in results:
                    if not isinstance(result, dict):
                        continue
                    rows = result.get("rows")
                    if not isinstance(rows, list):
                        continue
                    for row in rows:
                        if not isinstance(row, dict):
                            continue
                        inner = row.get("data")
                        spans.append(inner if isinstance(inner, dict) else row)
                if spans:
                    return spans
    result = payload.get("result")
    if isinstance(result, dict):
        candidates.append(result.get("data"))

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        spans = candidate.get("spans")
        if isinstance(spans, list):
            return [span for span in spans if isinstance(span, dict)]
    return []


def _trace_detail_hints(trace_details: list[dict[str, object]]) -> list[dict[str, str | None]]:
    hints: list[dict[str, str | None]] = []
    seen: set[tuple[str | None, str | None, str | None, str | None, str | None]] = set()

    for payload in trace_details:
        trace_id = _trace_id_from_payload(payload)
        for span in _trace_spans(payload):
            effective_trace_id = trace_id or _trace_id_from_payload(span)
            if effective_trace_id is None:
                continue
            hint = {
                "trace_id": effective_trace_id,
                "span_name": _span_attribute(span, "name"),
                "service_name": _span_attribute(span, "serviceName", "service.name", "peer.service"),
                "target": _span_attribute(
                    span,
                    "server.address",
                    "serverAddress",
                    "network.peer.address",
                    "http.url",
                    "httpUrl",
                ),
                "status_code": _span_attribute(
                    span,
                    "responseStatusCode",
                    "http.status_code",
                    "status.code",
                ),
            }
            identity = (
                hint["trace_id"],
                hint["span_name"],
                hint["service_name"],
                hint["target"],
                hint["status_code"],
            )
            if identity in seen:
                continue
            if not any((hint["span_name"], hint["service_name"], hint["target"], hint["status_code"])):
                continue
            seen.add(identity)
            hints.append(hint)
    return hints


def _prometheus_query_refs(queries: dict[str, str], *, endpoint_name: str | None) -> list[str]:
    return [_promql_ref(field, query=query, endpoint_name=endpoint_name) for field, query in queries.items() if query]


def build_prometheus_corroboration(
    normalized_alert: "NormalizedAlertGroup",
    *,
    repo_root: str | Path = Path("."),
    evidence_config_path: str | Path = _CONFIG_DEFAULT_PATH,
    prometheus_collector: PrometheusCollector | None = None,
    include_alertname_as_firing: bool = False,
) -> dict[str, object]:
    repo_root = Path(repo_root)
    config = load_evidence_collection_config(repo_root / evidence_config_path)
    service = str(normalized_alert.get("service") or "default")
    queries = _service_queries(service, config=config)
    endpoint_name = config.defaults.prometheus_endpoint
    alertname = _slug_alertname(normalized_alert.get("alertname"))

    evidence = {
        "alerts_firing": [alertname] if include_alertname_as_firing else [],
        "error_rate": None,
        "error_rate_baseline": None,
        "error_rate_delta": None,
        "latency_p95_ms": None,
        "latency_p95_baseline_ms": None,
        "latency_p95_delta": None,
        "qps": None,
        "qps_baseline": None,
        "qps_delta": None,
        "saturation": None,
    }
    if prometheus_collector is None:
        return evidence

    error_rate = _safe_prometheus_value(
        prometheus_collector,
        query=queries.get("error_rate", ""),
        endpoint_name=endpoint_name,
    ) if queries.get("error_rate") else None
    error_rate_baseline = _safe_prometheus_value(
        prometheus_collector,
        query=queries.get("error_rate_baseline", ""),
        endpoint_name=endpoint_name,
    ) if queries.get("error_rate_baseline") else None
    latency_p95_ms = _safe_prometheus_value(
        prometheus_collector,
        query=queries.get("latency_p95_ms", ""),
        endpoint_name=endpoint_name,
    ) if queries.get("latency_p95_ms") else None
    latency_p95_baseline_ms = _safe_prometheus_value(
        prometheus_collector,
        query=queries.get("latency_p95_baseline_ms", ""),
        endpoint_name=endpoint_name,
    ) if queries.get("latency_p95_baseline_ms") else None
    qps = _safe_prometheus_value(
        prometheus_collector,
        query=queries.get("qps", ""),
        endpoint_name=endpoint_name,
    ) if queries.get("qps") else None
    qps_baseline = _safe_prometheus_value(
        prometheus_collector,
        query=queries.get("qps_baseline", ""),
        endpoint_name=endpoint_name,
    ) if queries.get("qps_baseline") else None
    saturation = _safe_prometheus_value(
        prometheus_collector,
        query=queries.get("saturation", ""),
        endpoint_name=endpoint_name,
    ) if queries.get("saturation") else None

    evidence.update(
        {
            "error_rate": error_rate,
            "error_rate_baseline": error_rate_baseline,
            "error_rate_delta": (
                round(error_rate - error_rate_baseline, 4)
                if error_rate is not None and error_rate_baseline is not None
                else None
            ),
            "latency_p95_ms": latency_p95_ms,
            "latency_p95_baseline_ms": latency_p95_baseline_ms,
            "latency_p95_delta": (
                round(latency_p95_ms - latency_p95_baseline_ms, 4)
                if latency_p95_ms is not None and latency_p95_baseline_ms is not None
                else None
            ),
            "qps": qps,
            "qps_baseline": qps_baseline,
            "qps_delta": round(qps - qps_baseline, 4) if qps is not None and qps_baseline is not None else None,
            "saturation": saturation,
        }
    )
    return evidence


def _signoz_alert_context(normalized_alert: "NormalizedAlertGroup") -> dict[str, str | None]:
    source_refs = normalized_alert.get("source_refs") or {}
    severity = _string_value(source_refs.get("severity"))
    if severity is None:
        severity = normalized_alert.get("common_labels", {}).get("severity")
    return {
        "rule_id": _string_value(source_refs.get("rule_id")),
        "source_url": _string_value(source_refs.get("source_url")),
        "eval_window": _string_value(source_refs.get("eval_window")),
        "severity": severity,
    }


def _signoz_primary_refs(
    normalized_alert: "NormalizedAlertGroup",
    *,
    service: str,
    time_range: str,
    logs_limit: int,
    traces_limit: int,
    top_operations_limit: int,
    sample_trace_ids: list[str],
) -> list[str]:
    refs = [
        _signoz_ref(
            "logs",
            service=service,
            time_range=time_range,
            limit=logs_limit,
        ),
        _signoz_ref(
            "traces",
            service=service,
            time_range=time_range,
            limit=traces_limit,
        ),
        _signoz_ref(
            "top_operations",
            service=service,
            time_range=time_range,
            limit=top_operations_limit,
        ),
    ]

    alert_context = _signoz_alert_context(normalized_alert)
    if alert_context["rule_id"] or alert_context["source_url"]:
        refs.insert(
            0,
            _signoz_ref(
                "alert",
                rule_id=alert_context["rule_id"],
                service=service,
                source_url=alert_context["source_url"],
            ),
        )

    for trace_id in sample_trace_ids:
        refs.append(_signoz_ref("trace_detail", trace_id=trace_id, time_range=time_range))
        refs.append(_signoz_ref("logs_by_trace", trace_id=trace_id, time_range=time_range, limit=logs_limit))
    return refs


def build_signoz_first_evidence_bundle(
    normalized_alert: "NormalizedAlertGroup",
    *,
    repo_root: str | Path = Path("."),
    evidence_config_path: str | Path = _CONFIG_DEFAULT_PATH,
    services_config_path: str | Path = _SERVICES_CONFIG_PATH,
    prometheus_collector: PrometheusCollector | None = None,
    signoz_collector: SignozCollector | None = None,
    now: str | None = None,
) -> dict[str, object]:
    repo_root = Path(repo_root)
    config = load_evidence_collection_config(repo_root / evidence_config_path)
    service = str(normalized_alert.get("service") or "default")
    service_profile = load_service_profile(service, config_path=repo_root / services_config_path)
    signoz_collector = signoz_collector or SignozCollector()

    created_at = _iso_utc(now)
    window = _build_window(created_at=created_at, window_sec=config.defaults.window_sec)
    queries = _service_queries(service, config=config)
    endpoint_name = config.defaults.prometheus_endpoint

    traces = _safe_signoz_traces(
        signoz_collector,
        service=service,
        time_range=config.defaults.signoz_time_range,
        limit=config.defaults.signoz_traces_limit,
    )
    sample_trace_ids = _sample_trace_ids(traces, limit=config.defaults.signoz_traces_limit)

    operations = _safe_signoz_operations(
        signoz_collector,
        service=service,
        time_range=config.defaults.signoz_time_range,
    )[: config.defaults.signoz_top_operations_limit]
    service_logs = _safe_signoz_logs(
        signoz_collector,
        service=service,
        time_range=config.defaults.signoz_time_range,
        limit=config.defaults.signoz_logs_limit,
    )

    trace_details = [
        payload
        for payload in (
            _safe_signoz_trace_details(
                signoz_collector,
                trace_id=trace_id,
                time_range=config.defaults.signoz_time_range,
            )
            for trace_id in sample_trace_ids[: config.defaults.signoz_trace_details_limit]
        )
        if payload is not None
    ]

    trace_logs: list[dict[str, object]] = []
    if not service_logs:
        for trace_id in sample_trace_ids[: config.defaults.signoz_trace_details_limit]:
            trace_logs.extend(
                _safe_signoz_trace_logs(
                    signoz_collector,
                    trace_id=trace_id,
                    time_range=config.defaults.signoz_time_range,
                    limit=config.defaults.signoz_trace_logs_limit,
                )
            )
            if trace_logs:
                break

    logs = service_logs or trace_logs
    top_error_templates = _top_error_templates(
        logs,
        normalized_alert=normalized_alert,
        fallback_novelty_score=config.defaults.fallback_novelty_score,
        fallback_error_template_count=config.defaults.fallback_error_template_count,
    )
    top_slow_operations = _top_slow_operations(operations, normalized_alert=normalized_alert)
    trace_detail_hints = _trace_detail_hints(trace_details)
    alert_context = _signoz_alert_context(normalized_alert)

    return {
        "created_at": created_at,
        "window": window,
        "prometheus": build_prometheus_corroboration(
            normalized_alert,
            repo_root=repo_root,
            evidence_config_path=evidence_config_path,
            prometheus_collector=prometheus_collector,
            include_alertname_as_firing=False,
        ),
        "signoz": {
            "top_error_templates": top_error_templates,
            "top_slow_operations": top_slow_operations,
            "trace_error_ratio": _trace_error_ratio(traces),
            "sample_trace_ids": sample_trace_ids,
            "sample_log_refs": [
                f"signoz-mcp://log-row/{row.get('id') or index}"
                for index, row in enumerate(logs[: config.defaults.signoz_logs_limit], start=1)
            ],
            "alert_context": alert_context,
            "trace_detail_hints": trace_detail_hints,
        },
        "topology": {
            "tier": service_profile.tier,
            "owner": service_profile.owner_hint,
            "repo_candidates": list(service_profile.repo_hints),
            "upstream_count": service_profile.upstream_count,
            "downstream_count": service_profile.downstream_count,
            "blast_radius_score": service_profile.blast_radius_score,
        },
        "history": {
            "recent_deploy": False,
            "similar_incident_ids": [],
            "similar_packet_ids": [],
        },
        "evidence_refs": {
            "prometheus_query_refs": _prometheus_query_refs(queries, endpoint_name=endpoint_name),
            "signoz_query_refs": _signoz_primary_refs(
                normalized_alert,
                service=service,
                time_range=config.defaults.signoz_time_range,
                logs_limit=config.defaults.signoz_trace_logs_limit,
                traces_limit=config.defaults.signoz_traces_limit,
                top_operations_limit=config.defaults.signoz_top_operations_limit,
                sample_trace_ids=sample_trace_ids[: config.defaults.signoz_trace_details_limit],
            ),
        },
    }


def build_live_evidence_bundle(
    normalized_alert: "NormalizedAlertGroup",
    *,
    repo_root: str | Path = Path("."),
    evidence_config_path: str | Path = _CONFIG_DEFAULT_PATH,
    services_config_path: str | Path = _SERVICES_CONFIG_PATH,
    prometheus_collector: PrometheusCollector | None = None,
    signoz_collector: SignozCollector | None = None,
    now: str | None = None,
) -> dict[str, object]:
    repo_root = Path(repo_root)
    config = load_evidence_collection_config(repo_root / evidence_config_path)
    service = str(normalized_alert.get("service") or "default")
    service_profile = load_service_profile(service, config_path=repo_root / services_config_path)
    prometheus_collector = prometheus_collector or PrometheusCollector()
    signoz_collector = signoz_collector or SignozCollector()

    created_at = _iso_utc(now)
    window = _build_window(created_at=created_at, window_sec=config.defaults.window_sec)
    queries = _service_queries(service, config=config)
    endpoint_name = config.defaults.prometheus_endpoint

    prometheus = build_prometheus_corroboration(
        normalized_alert,
        repo_root=repo_root,
        evidence_config_path=evidence_config_path,
        prometheus_collector=prometheus_collector,
        include_alertname_as_firing=True,
    )

    logs = _safe_signoz_logs(
        signoz_collector,
        service=service,
        time_range=config.defaults.signoz_time_range,
        limit=config.defaults.signoz_logs_limit,
    )
    traces = _safe_signoz_traces(
        signoz_collector,
        service=service,
        time_range=config.defaults.signoz_time_range,
        limit=config.defaults.signoz_traces_limit,
    )
    operations = _safe_signoz_operations(
        signoz_collector,
        service=service,
        time_range=config.defaults.signoz_time_range,
    )[: config.defaults.signoz_top_operations_limit]

    top_error_templates = _top_error_templates(
        logs,
        normalized_alert=normalized_alert,
        fallback_novelty_score=config.defaults.fallback_novelty_score,
        fallback_error_template_count=config.defaults.fallback_error_template_count,
    )
    top_slow_operations = _top_slow_operations(operations, normalized_alert=normalized_alert)
    sample_trace_ids = _sample_trace_ids(traces, limit=config.defaults.signoz_traces_limit)

    return {
        "created_at": created_at,
        "window": window,
        "prometheus": prometheus,
        "signoz": {
            "top_error_templates": top_error_templates,
            "top_slow_operations": top_slow_operations,
            "trace_error_ratio": _trace_error_ratio(traces),
            "sample_trace_ids": sample_trace_ids,
            "sample_log_refs": [
                f"signoz-mcp://log-row/{row.get('id') or index}"
                for index, row in enumerate(logs[: config.defaults.signoz_logs_limit], start=1)
            ],
        },
        "topology": {
            "tier": service_profile.tier,
            "owner": service_profile.owner_hint,
            "repo_candidates": list(service_profile.repo_hints),
            "upstream_count": service_profile.upstream_count,
            "downstream_count": service_profile.downstream_count,
            "blast_radius_score": service_profile.blast_radius_score,
        },
        "history": {
            "recent_deploy": False,
            "similar_incident_ids": [],
            "similar_packet_ids": [],
        },
        "evidence_refs": {
            "prometheus_query_refs": _prometheus_query_refs(queries, endpoint_name=endpoint_name),
            "signoz_query_refs": [
                _signoz_ref(
                    "logs",
                    service=service,
                    time_range=config.defaults.signoz_time_range,
                    limit=config.defaults.signoz_logs_limit,
                ),
                _signoz_ref(
                    "traces",
                    service=service,
                    time_range=config.defaults.signoz_time_range,
                    limit=config.defaults.signoz_traces_limit,
                ),
                _signoz_ref(
                    "top_operations",
                    service=service,
                    time_range=config.defaults.signoz_time_range,
                    limit=config.defaults.signoz_top_operations_limit,
                ),
            ],
        },
    }
