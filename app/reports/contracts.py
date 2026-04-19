"""Base contract surface for alert report frontmatter and body ordering."""

from __future__ import annotations

from pathlib import Path
from typing import Final, Literal, TypedDict

from app.contracts_common import DATA_DIR, load_json_schema, schema_path

SCHEMA_VERSION: Final = "alert-report.v1"
SCHEMA_FILE: Final = "alert-report-frontmatter.v1.json"
SCHEMA_PATH: Final[Path] = schema_path(SCHEMA_FILE)
ARTIFACT_DIR: Final[Path] = DATA_DIR / "reports"

SeverityBand = Literal["P1", "P2", "P3", "P4"]
DeliveryClass = Literal["observe", "open_ticket", "page_owner", "send_to_human_review"]

BODY_SECTION_ORDER: Final[list[str]] = [
    "Executive Summary",
    "Why This Alert Exists",
    "Metric Signals",
    "Logs And Traces",
    "Investigation",
    "Impact And Routing",
    "Recommended Action",
    "Evidence Refs",
    "Unknowns",
]


class AlertReportFrontmatter(TypedDict):
    schema_version: str
    report_id: str
    packet_id: str
    decision_id: str
    generated_at: str
    severity_band: SeverityBand
    delivery_class: DeliveryClass
    investigation_stage: Literal["none", "local_primary", "cloud_fallback"]
    service: str
    operation: str | None
    owner: str | None
    repo_candidates: list[str]
    prometheus_ref_ids: list[str]
    signoz_ref_ids: list[str]


def load_schema() -> dict[str, object]:
    return load_json_schema(SCHEMA_FILE)
