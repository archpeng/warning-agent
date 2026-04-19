from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_contract_inventory_uses_investigation_result_canonical_name() -> None:
    inventory = (REPO_ROOT / "docs" / "warning-agent-contract-inventory.md").read_text(
        encoding="utf-8"
    )

    assert "investigation-result.v1" in inventory
    assert "`needs_cloud_investigation` / `cloud_trigger_reasons`" in inventory
    assert "不再使用旧的 cloud-specific 表述" in inventory
