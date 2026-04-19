from __future__ import annotations

import json
from pathlib import Path

from app.analyzer import contracts as analyzer_contracts
from app.investigator import contracts as investigator_contracts
from app.packet import contracts as packet_contracts
from app.reports import contracts as report_contracts


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILES = {
    "incident-packet.v1.json": (packet_contracts, "incident-packet.v1"),
    "local-analyzer-decision.v1.json": (analyzer_contracts, "local-analyzer-decision.v1"),
    "investigation-result.v1.json": (investigator_contracts, "investigation-result.v1"),
    "alert-report-frontmatter.v1.json": (report_contracts, "alert-report.v1"),
}


def test_schema_files_load_as_json() -> None:
    schema_dir = REPO_ROOT / "schemas"

    for file_name in SCHEMA_FILES:
        with (schema_dir / file_name).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert payload["title"]


def test_contract_modules_load_matching_schema_versions() -> None:
    for file_name, (module, schema_version) in SCHEMA_FILES.items():
        payload = module.load_schema()
        assert payload["title"] in {schema_version, "alert-report-frontmatter.v1"}
        assert module.SCHEMA_FILE == file_name
        assert module.SCHEMA_PATH.name == file_name
        assert module.SCHEMA_VERSION == schema_version


def test_report_section_order_is_frozen() -> None:
    assert report_contracts.BODY_SECTION_ORDER == [
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
