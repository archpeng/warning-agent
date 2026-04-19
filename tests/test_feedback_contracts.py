from __future__ import annotations

import copy

import pytest
from jsonschema import Draft202012Validator

from app.feedback.contracts import SCHEMA_PATH, IncidentOutcome, load_schema
from app.feedback.persistence import validate_outcome_record


@pytest.fixture()
def sample_outcome() -> IncidentOutcome:
    return {
        "schema_version": "incident-outcome.v1",
        "outcome_id": "out_checkout_post_pay_20260419t080000z",
        "source": "operator",
        "recorded_at": "2026-04-19T08:00:00Z",
        "service": "checkout",
        "operation": "POST /api/pay",
        "environment": "prod",
        "input_refs": {
            "packet_id": "ipk_checkout_post_api_pay_20260418t120008z",
            "decision_id": "lad_checkout_post_pay_20260418t120010z",
            "investigation_id": "inv_checkout_post_pay_20260418t120012z",
            "report_id": "rpt_checkout_post_api_pay_20260418t120008z",
        },
        "summary": {
            "known_outcome": "severe",
            "final_severity_band": "P1",
            "final_recommended_action": "page_owner",
            "resolution_summary": "operator confirmed a real checkout timeout regression and mitigated it with a rollback",
        },
        "notes": [
            "rollback completed before customer-facing latency returned to baseline",
        ],
        "evidence_links": {
            "ticket_id": "INC-4242",
            "postmortem_id": "PM-2026-04-19-checkout",
        },
    }


def test_incident_outcome_contract_loads_schema_from_repo() -> None:
    schema = load_schema()

    assert SCHEMA_PATH.name == "incident-outcome.v1.json"
    assert schema["properties"]["schema_version"]["const"] == "incident-outcome.v1"


def test_validate_outcome_record_accepts_schema_valid_artifact(sample_outcome: IncidentOutcome) -> None:
    validator = Draft202012Validator(load_schema())
    errors = sorted(validator.iter_errors(sample_outcome), key=lambda error: error.json_path)

    assert errors == []
    validate_outcome_record(sample_outcome)


def test_validate_outcome_record_rejects_missing_required_summary_field(sample_outcome: IncidentOutcome) -> None:
    invalid = copy.deepcopy(sample_outcome)
    invalid["summary"].pop("known_outcome")

    with pytest.raises(ValueError, match="known_outcome"):
        validate_outcome_record(invalid)
