"""Temporal robustness corpus loader for W3 packet.v2 preparation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final, TypedDict

from app.packet.contracts import TemporalContextV2

TEMPORAL_ROBUSTNESS_CORPUS_SCHEMA_VERSION: Final = "local-analyzer-temporal-robustness-corpus.v1"


class TemporalRobustnessVariant(TypedDict):
    variant_id: str
    time_offset_minutes: int
    evidence_fixture: str
    temporal_context: TemporalContextV2
    expected_needs_investigation: bool
    expected_severity_band: str


class TemporalRobustnessCase(TypedDict):
    case_id: str
    replay_fixture: str
    variants: list[TemporalRobustnessVariant]


def load_temporal_robustness_corpus(
    path: str | Path,
) -> tuple[str, list[TemporalRobustnessCase]]:
    corpus_path = Path(path)
    with corpus_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    schema_version = payload.get("schema_version")
    if schema_version != TEMPORAL_ROBUSTNESS_CORPUS_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported temporal robustness corpus schema: {schema_version} != {TEMPORAL_ROBUSTNESS_CORPUS_SCHEMA_VERSION}"
        )

    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("temporal robustness corpus must contain non-empty cases")

    for case in cases:
        if not isinstance(case.get("variants"), list) or not case["variants"]:
            raise ValueError(f"temporal robustness case {case.get('case_id')} must contain variants")

    return schema_version, cases
