from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture
from app.reports.contracts import BODY_SECTION_ORDER, load_schema as load_report_schema
from app.reports.markdown_builder import render_alert_report


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"
EVIDENCE_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.packet-input.json"
DECISION_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.local-decision.json"
INVESTIGATION_FIXTURE = REPO_ROOT / "fixtures" / "evidence" / "checkout.local-investigation.json"
GOLDEN_REPORT = REPO_ROOT / "fixtures" / "reports" / "checkout.expected.md"
GOLDEN_INVESTIGATION_REPORT = REPO_ROOT / "fixtures" / "reports" / "checkout.with-investigation.expected.md"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_markdown_builder_renders_schema_valid_frontmatter_and_golden_body() -> None:
    replay = load_manual_replay_fixture(REPLAY_FIXTURE)
    normalized = normalize_alertmanager_payload(
        replay["alert_payload"],
        candidate_source="manual_replay",
    )
    packet = build_incident_packet_from_bundle(normalized, _load_json(EVIDENCE_FIXTURE))
    decision = _load_json(DECISION_FIXTURE)

    report = render_alert_report(packet, decision)
    expected = GOLDEN_REPORT.read_text(encoding="utf-8")

    assert report == expected

    _, frontmatter_block, body = report.split("---", maxsplit=2)
    frontmatter = yaml.safe_load(frontmatter_block)
    validator = Draft202012Validator(load_report_schema())
    errors = sorted(validator.iter_errors(frontmatter), key=lambda error: error.json_path)

    assert not errors
    headings = [line.removeprefix("## ") for line in body.splitlines() if line.startswith("## ")]
    assert headings == BODY_SECTION_ORDER


def test_markdown_builder_renders_local_primary_investigation_golden_report() -> None:
    replay = load_manual_replay_fixture(REPLAY_FIXTURE)
    normalized = normalize_alertmanager_payload(
        replay["alert_payload"],
        candidate_source="manual_replay",
    )
    packet = build_incident_packet_from_bundle(normalized, _load_json(EVIDENCE_FIXTURE))
    decision = _load_json(DECISION_FIXTURE)
    investigation = _load_json(INVESTIGATION_FIXTURE)

    report = render_alert_report(packet, decision, investigation)
    expected = GOLDEN_INVESTIGATION_REPORT.read_text(encoding="utf-8")

    assert report == expected

    _, frontmatter_block, body = report.split("---", maxsplit=2)
    frontmatter = yaml.safe_load(frontmatter_block)
    validator = Draft202012Validator(load_report_schema())
    errors = sorted(validator.iter_errors(frontmatter), key=lambda error: error.json_path)

    assert not errors
    assert frontmatter["investigation_stage"] == "local_primary"
    headings = [line.removeprefix("## ") for line in body.splitlines() if line.startswith("## ")]
    assert headings == BODY_SECTION_ORDER
