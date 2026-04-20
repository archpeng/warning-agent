from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE_DOC = REPO_ROOT / "docs" / "warning-agent-architecture.md"
PROVIDER_BOUNDARY_DOC = REPO_ROOT / "docs" / "warning-agent-provider-boundary.md"
GUARDRAILS_DOC = REPO_ROOT / "docs" / "warning-agent-architecture-clarity-guardrails.md"
TARGET_MAP_DOC = REPO_ROOT / "docs" / "warning-agent-architecture-clarity-target-map.md"
FUTURE_NOTE_DOC = (
    REPO_ROOT / "docs" / "future" / "warning-agent-3.5-3.6-learning-optimization-minimal-engineering.md"
)



def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")



def test_architecture_clarity_guardrails_freeze_no_overengineering_and_hotspots() -> None:
    text = _read(GUARDRAILS_DOC)

    assert "keep the shell" in text
    assert "no generic framework jump" in text
    assert "no warning-core extraction" in text
    assert "app/investigator/local_primary.py" in text
    assert "app/investigator/cloud_fallback.py" in text
    assert "app/runtime_entry.py" in text
    assert "app/analyzer/trained_scorer.py" in text
    assert "app/analyzer/calibrate.py" in text
    assert "SidecarAssistPacket" in text
    assert "ActionTrace" in text



def test_architecture_clarity_target_map_freezes_move_targets_for_3_5_and_3_6() -> None:
    text = _read(TARGET_MAP_DOC)

    assert "Runtime vs benchmark ownership inventory" in text
    assert "AC.S2a" in text
    assert "AC.S2b" in text
    assert "AC.S3a" in text
    assert "AC.S3b" in text
    assert "AC.S3c" in text
    assert "packet -> receiver" in text
    assert "normalized alert types" in text
    assert "package `__init__` exports" in text



def test_core_docs_reference_the_architecture_clarity_guardrails() -> None:
    architecture = _read(ARCHITECTURE_DOC)
    provider_boundary = _read(PROVIDER_BOUNDARY_DOC)
    future_note = _read(FUTURE_NOTE_DOC)

    assert "warning-agent-architecture-clarity-guardrails.md" in architecture
    assert "warning-agent-architecture-clarity-target-map.md" in architecture
    assert "Current architecture-clarity split rule" in provider_boundary
    assert "warning-agent-architecture-clarity-optimization-2026-04-20_PLAN.md" in future_note
    assert "只有当 architecture-clarity pack 已证明 `3.5 / 3.6` ownership 更清楚时" in future_note
