from __future__ import annotations

import json
from pathlib import Path

import httpx

from app.delivery.adapter_feishu import build_adapter_feishu_notification_payload, serialize_adapter_feishu_notification_payload
from app.delivery.bridge_result import BridgeDispatchResult
from app.delivery.env_gate import resolve_adapter_feishu_env_gate
from app.delivery.http_client import post_adapter_feishu_notification
from app.delivery.runtime import EnvGatedLiveRoute, FeishuTargetEnvConfig, persist_report_delivery
from app.storage.artifact_store import JSONLArtifactStore


REPO_ROOT = Path(__file__).resolve().parents[1]


def _report_record() -> dict[str, object]:
    return {
        "schema_version": "alert-report.v1",
        "report_id": "rpt_checkout_post_api_pay_20260418t120008z",
        "packet_id": "ipk_checkout_post_api_pay_20260418t120008z",
        "decision_id": "lad_checkout_post_pay_20260418t120010z",
        "generated_at": "2026-04-18T12:00:24Z",
        "severity_band": "P1",
        "delivery_class": "page_owner",
        "investigation_stage": "cloud_fallback",
        "service": "checkout",
        "operation": "POST /api/pay",
        "owner": "payments-oncall",
        "repo_candidates": ["checkout-service"],
        "prometheus_ref_ids": ["prom://query/high_error_rate_window_300s"],
        "signoz_ref_ids": ["signoz://trace/query-123"],
        "markdown": "---\nschema_version: alert-report.v1\nreport_id: rpt_checkout_post_api_pay_20260418t120008z\n---\n\n## Executive Summary\n- service: `checkout`\n",
    }



def _page_owner_route() -> EnvGatedLiveRoute:
    return EnvGatedLiveRoute(
        delivery_class="page_owner",
        adapter="adapter_feishu",
        delivery_mode="env_gated_live",
        provider_key="warning-agent",
        endpoint_env="WARNING_AGENT_ADAPTER_FEISHU_BASE_URL",
        timeout_seconds=5,
        target=FeishuTargetEnvConfig(
            channel="feishu",
            chat_id_env="WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID",
            open_id_env="WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID",
            thread_id_env="WARNING_AGENT_ADAPTER_FEISHU_THREAD_ID",
        ),
    )



def test_resolve_adapter_feishu_env_gate_ready_with_chat_id(monkeypatch) -> None:
    monkeypatch.setenv("WARNING_AGENT_ADAPTER_FEISHU_BASE_URL", "http://127.0.0.1:8787/")
    monkeypatch.setenv("WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID", "oc-test-chat")
    monkeypatch.delenv("WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID", raising=False)
    monkeypatch.delenv("WARNING_AGENT_ADAPTER_FEISHU_THREAD_ID", raising=False)

    resolution = resolve_adapter_feishu_env_gate(_page_owner_route())

    assert resolution.state == "ready"
    assert resolution.endpoint == "http://127.0.0.1:8787"
    assert resolution.target is not None
    assert resolution.target.chat_id == "oc-test-chat"
    assert resolution.target.open_id is None
    assert resolution.target.thread_id is None
    assert resolution.missing_env == ()



def test_resolve_adapter_feishu_env_gate_ready_with_open_id_only(monkeypatch) -> None:
    monkeypatch.setenv("WARNING_AGENT_ADAPTER_FEISHU_BASE_URL", "http://127.0.0.1:8787")
    monkeypatch.delenv("WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID", raising=False)
    monkeypatch.setenv("WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID", "ou_test_open_id")

    resolution = resolve_adapter_feishu_env_gate(_page_owner_route())

    assert resolution.state == "ready"
    assert resolution.target is not None
    assert resolution.target.chat_id is None
    assert resolution.target.open_id == "ou_test_open_id"



def test_resolve_adapter_feishu_env_gate_missing_endpoint(monkeypatch) -> None:
    monkeypatch.delenv("WARNING_AGENT_ADAPTER_FEISHU_BASE_URL", raising=False)
    monkeypatch.setenv("WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID", "oc-test-chat")

    resolution = resolve_adapter_feishu_env_gate(_page_owner_route())

    assert resolution.state == "missing_env"
    assert resolution.endpoint is None
    assert resolution.target is None
    assert resolution.missing_env == ("WARNING_AGENT_ADAPTER_FEISHU_BASE_URL",)



def test_resolve_adapter_feishu_env_gate_missing_target(monkeypatch) -> None:
    monkeypatch.setenv("WARNING_AGENT_ADAPTER_FEISHU_BASE_URL", "http://127.0.0.1:8787")
    monkeypatch.delenv("WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID", raising=False)
    monkeypatch.delenv("WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID", raising=False)

    resolution = resolve_adapter_feishu_env_gate(_page_owner_route())

    assert resolution.state == "missing_env"
    assert resolution.endpoint == "http://127.0.0.1:8787"
    assert resolution.target is None
    assert resolution.missing_env == (
        "WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID",
        "WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID",
    )



def test_build_adapter_feishu_notification_payload_maps_report_record() -> None:
    resolution = resolve_adapter_feishu_env_gate(
        _page_owner_route(),
        env={
            "WARNING_AGENT_ADAPTER_FEISHU_BASE_URL": "http://127.0.0.1:8787",
            "WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID": "oc-test-chat",
            "WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID": None,
            "WARNING_AGENT_ADAPTER_FEISHU_THREAD_ID": None,
        },
    )
    assert resolution.target is not None

    payload = build_adapter_feishu_notification_payload(_report_record(), target=resolution.target)
    serialized = serialize_adapter_feishu_notification_payload(payload)

    assert serialized["providerKey"] == "warning-agent"
    assert serialized["reportId"] == "rpt_checkout_post_api_pay_20260418t120008z"
    assert serialized["runId"] == "ipk_checkout_post_api_pay_20260418t120008z"
    assert serialized["title"] == "[P1] checkout POST /api/pay"
    assert serialized["summary"] == "checkout POST /api/pay requires page_owner after cloud_fallback investigation"
    assert serialized["severity"] == "critical"
    assert serialized["bodyMarkdown"].startswith("---\nschema_version: alert-report.v1")
    assert serialized["target"] == {"channel": "feishu", "chatId": "oc-test-chat"}
    assert serialized["facts"] == [
        {"label": "service", "value": "checkout"},
        {"label": "operation", "value": "POST /api/pay"},
        {"label": "delivery_class", "value": "page_owner"},
        {"label": "investigation_stage", "value": "cloud_fallback"},
        {"label": "owner", "value": "payments-oncall"},
    ]



def test_build_adapter_feishu_notification_payload_omits_optional_fields_when_absent() -> None:
    resolution = resolve_adapter_feishu_env_gate(
        _page_owner_route(),
        env={
            "WARNING_AGENT_ADAPTER_FEISHU_BASE_URL": "http://127.0.0.1:8787",
            "WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID": None,
            "WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID": "ou_test_open_id",
            "WARNING_AGENT_ADAPTER_FEISHU_THREAD_ID": None,
        },
    )
    assert resolution.target is not None
    report_record = _report_record() | {"service": "inventory", "operation": None, "owner": None, "severity_band": "P2"}

    payload = build_adapter_feishu_notification_payload(report_record, target=resolution.target)
    serialized = serialize_adapter_feishu_notification_payload(payload)

    assert serialized["title"] == "[P2] inventory"
    assert serialized["summary"] == "inventory requires page_owner after cloud_fallback investigation"
    assert serialized["severity"] == "warning"
    assert serialized["target"] == {"channel": "feishu", "openId": "ou_test_open_id"}
    assert serialized["facts"] == [
        {"label": "service", "value": "inventory"},
        {"label": "delivery_class", "value": "page_owner"},
        {"label": "investigation_stage", "value": "cloud_fallback"},
    ]



def test_post_adapter_feishu_notification_returns_delivered_for_adapter_success(monkeypatch) -> None:
    def fake_post(url: str, *, json: dict[str, object], timeout: float) -> httpx.Response:
        assert url == "http://127.0.0.1:8787/providers/webhook"
        assert json["providerKey"] == "warning-agent"
        assert timeout == 5
        return httpx.Response(
            202,
            json={"code": 0, "providerKey": "warning-agent", "status": "delivered"},
        )

    monkeypatch.setattr("app.delivery.http_client.httpx.post", fake_post)

    result = post_adapter_feishu_notification(
        endpoint="http://127.0.0.1:8787/providers/webhook",
        payload={"providerKey": "warning-agent"},
        timeout_seconds=5,
    )

    assert result.status == "delivered"
    assert result.response_code == 202
    assert result.provider_key == "warning-agent"
    assert result.provider_status == "delivered"
    assert result.raw_response == {"code": 0, "providerKey": "warning-agent", "status": "delivered"}



def test_post_adapter_feishu_notification_treats_duplicate_ignored_as_delivered(monkeypatch) -> None:
    def fake_post(url: str, *, json: dict[str, object], timeout: float) -> httpx.Response:
        return httpx.Response(
            202,
            json={"code": 0, "providerKey": "warning-agent", "status": "duplicate_ignored"},
        )

    monkeypatch.setattr("app.delivery.http_client.httpx.post", fake_post)

    result = post_adapter_feishu_notification(
        endpoint="http://127.0.0.1:8787/providers/webhook",
        payload={"providerKey": "warning-agent"},
        timeout_seconds=5,
    )

    assert result.status == "delivered"
    assert result.response_code == 202
    assert result.provider_status == "duplicate_ignored"



def test_post_adapter_feishu_notification_returns_failed_for_malformed_response(monkeypatch) -> None:
    def fake_post(url: str, *, json: dict[str, object], timeout: float) -> httpx.Response:
        return httpx.Response(202, json={"code": 7, "status": "unexpected"})

    monkeypatch.setattr("app.delivery.http_client.httpx.post", fake_post)

    result = post_adapter_feishu_notification(
        endpoint="http://127.0.0.1:8787/providers/webhook",
        payload={"providerKey": "warning-agent"},
        timeout_seconds=5,
    )

    assert result.status == "failed"
    assert result.response_code == 202
    assert result.provider_status == "unexpected"
    assert result.message == "adapter_feishu_rejected"



def test_persist_report_delivery_marks_page_owner_deferred_when_env_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("WARNING_AGENT_ADAPTER_FEISHU_BASE_URL", raising=False)
    monkeypatch.delenv("WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID", raising=False)
    monkeypatch.delenv("WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID", raising=False)
    monkeypatch.delenv("WARNING_AGENT_ADAPTER_FEISHU_THREAD_ID", raising=False)
    artifact_store = JSONLArtifactStore(root=tmp_path)

    dispatch = persist_report_delivery(
        report_record=_report_record(),
        artifact_store=artifact_store,
        config_path=REPO_ROOT / "configs" / "delivery.yaml",
    )

    assert dispatch.payload_path.exists()
    assert dispatch.bridge_payload_path is None
    assert dispatch.record["route_adapter"] == "adapter_feishu"
    assert dispatch.record["delivery_mode"] == "env_gated_live"
    assert dispatch.record["status"] == "deferred"
    assert dispatch.record["env_gate_state"] == "missing_env"
    assert dispatch.record["queue"] is None
    assert dispatch.record["target_channel"] == "feishu"
    assert dispatch.record["target_ref"] is None
    assert dispatch.record["live_endpoint"] is None
    assert dispatch.record["missing_env"] == [
        "WARNING_AGENT_ADAPTER_FEISHU_BASE_URL",
        "WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID",
        "WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID",
    ]



def test_persist_report_delivery_marks_page_owner_delivered_when_bridge_succeeds(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WARNING_AGENT_ADAPTER_FEISHU_BASE_URL", "http://127.0.0.1:8787/")
    monkeypatch.setenv("WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID", "oc-test-chat")
    monkeypatch.delenv("WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID", raising=False)
    monkeypatch.delenv("WARNING_AGENT_ADAPTER_FEISHU_THREAD_ID", raising=False)
    monkeypatch.setattr(
        "app.delivery.runtime.post_adapter_feishu_notification",
        lambda endpoint, payload, timeout_seconds: BridgeDispatchResult(
            status="delivered",
            response_code=202,
            provider_key="warning-agent",
            provider_status="delivered",
            message=None,
            external_ref="msg-1",
            raw_response={"code": 0, "providerKey": "warning-agent", "status": "delivered"},
        ),
    )
    artifact_store = JSONLArtifactStore(root=tmp_path)

    dispatch = persist_report_delivery(
        report_record=_report_record(),
        artifact_store=artifact_store,
        config_path=REPO_ROOT / "configs" / "delivery.yaml",
    )

    assert dispatch.payload_path.exists()
    assert dispatch.bridge_payload_path is not None
    assert dispatch.bridge_payload_path.exists()
    assert dispatch.record["route_adapter"] == "adapter_feishu"
    assert dispatch.record["delivery_mode"] == "env_gated_live"
    assert dispatch.record["status"] == "delivered"
    assert dispatch.record["env_gate_state"] == "ready"
    assert dispatch.record["response_code"] == 202
    assert dispatch.record["provider_key"] == "warning-agent"
    assert dispatch.record["provider_status"] == "delivered"
    assert dispatch.record["external_ref"] == "msg-1"
    assert dispatch.record["target_ref"] == "oc-test-chat"
    assert dispatch.record["live_endpoint"] == "http://127.0.0.1:8787/providers/webhook"
    payload = json.loads(dispatch.bridge_payload_path.read_text(encoding="utf-8"))
    assert payload["providerKey"] == "warning-agent"
    assert payload["target"] == {"channel": "feishu", "chatId": "oc-test-chat"}



def test_persist_report_delivery_marks_page_owner_failed_when_bridge_fails(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WARNING_AGENT_ADAPTER_FEISHU_BASE_URL", "http://127.0.0.1:8787/")
    monkeypatch.setenv("WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID", "oc-test-chat")
    monkeypatch.delenv("WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID", raising=False)
    monkeypatch.delenv("WARNING_AGENT_ADAPTER_FEISHU_THREAD_ID", raising=False)
    monkeypatch.setattr(
        "app.delivery.runtime.post_adapter_feishu_notification",
        lambda endpoint, payload, timeout_seconds: BridgeDispatchResult(
            status="failed",
            response_code=502,
            provider_key="warning-agent",
            provider_status=None,
            message="adapter_feishu_rejected",
            external_ref=None,
            raw_response={"code": 7},
        ),
    )
    artifact_store = JSONLArtifactStore(root=tmp_path)

    dispatch = persist_report_delivery(
        report_record=_report_record(),
        artifact_store=artifact_store,
        config_path=REPO_ROOT / "configs" / "delivery.yaml",
    )

    assert dispatch.record["status"] == "failed"
    assert dispatch.record["response_code"] == 502
    assert dispatch.record["provider_key"] == "warning-agent"
    assert dispatch.record["provider_status"] is None
    assert dispatch.record["error_message"] == "adapter_feishu_rejected"
