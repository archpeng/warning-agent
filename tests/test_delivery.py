from __future__ import annotations

from pathlib import Path

from app.delivery.runtime import load_delivery_config, persist_report_delivery
from app.storage.artifact_store import JSONLArtifactStore


REPO_ROOT = Path(__file__).resolve().parents[1]



def _report_record(delivery_class: str = "page_owner") -> dict[str, object]:
    return {
        "schema_version": "alert-report.v1",
        "report_id": "rpt_checkout_post_api_pay_20260418t120008z",
        "packet_id": "ipk_checkout_post_api_pay_20260418t120008z",
        "decision_id": "lad_checkout_post_pay_20260418t120010z",
        "generated_at": "2026-04-18T12:00:24Z",
        "severity_band": "P1",
        "delivery_class": delivery_class,
        "investigation_stage": "cloud_fallback",
        "service": "checkout",
        "operation": "POST /api/pay",
        "owner": "payments-oncall",
        "repo_candidates": ["checkout-service"],
        "prometheus_ref_ids": ["prom://query/high_error_rate_window_300s"],
        "signoz_ref_ids": ["signoz://trace/query-123"],
        "markdown": "---\nschema_version: alert-report.v1\nreport_id: rpt_checkout_post_api_pay_20260418t120008z\n---\n\n## Executive Summary\n- service: `checkout`\n",
    }



def test_load_delivery_config_maps_local_routes() -> None:
    config = load_delivery_config(REPO_ROOT / "configs" / "delivery.yaml")

    assert config.routes["observe"].adapter == "markdown_only"
    assert config.routes["page_owner"].adapter == "local_page_queue"
    assert config.routes["open_ticket"].queue == "ticket_queue"
    assert config.routes["send_to_human_review"].queue == "review_queue"



def test_persist_report_delivery_writes_dispatch_record_and_markdown_snapshot(tmp_path: Path) -> None:
    artifact_store = JSONLArtifactStore(root=tmp_path)

    dispatch = persist_report_delivery(
        report_record=_report_record("page_owner"),
        artifact_store=artifact_store,
        config_path=REPO_ROOT / "configs" / "delivery.yaml",
    )

    assert dispatch.dispatch_path == tmp_path / "deliveries" / "deliveries.jsonl"
    assert dispatch.payload_path.exists()
    assert dispatch.record["delivery_class"] == "page_owner"
    assert dispatch.record["route_adapter"] == "local_page_queue"
    assert dispatch.record["queue"] == "page_queue"
    assert dispatch.record["payload_path"] == str(dispatch.payload_path)
    assert artifact_store.read_all("deliveries") == [dispatch.record]
    assert "## Executive Summary" in dispatch.payload_path.read_text(encoding="utf-8")
