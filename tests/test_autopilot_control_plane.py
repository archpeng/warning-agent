from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_ROOT = REPO_ROOT / "docs" / "plan"
README_PATH = PLAN_ROOT / "README.md"
ACTIVE_PLAN_PATH = PLAN_ROOT / "active_PLAN.md"
ACTIVE_STATUS_PATH = PLAN_ROOT / "active_STATUS.md"
ACTIVE_WORKSET_PATH = PLAN_ROOT / "active_WORKSET.md"
SOURCE_PLAN_PATH = PLAN_ROOT / "warning-agent-warning-plane-production-stability-2026-04-20_PLAN.md"
SOURCE_STATUS_PATH = PLAN_ROOT / "warning-agent-warning-plane-production-stability-2026-04-20_STATUS.md"
SOURCE_WORKSET_PATH = PLAN_ROOT / "warning-agent-warning-plane-production-stability-2026-04-20_WORKSET.md"



def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")



def _section(markdown: str, heading: str) -> str:
    lines = markdown.splitlines()
    header = f"## {heading}"
    start = lines.index(header)
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        body.append(line)
    return "\n".join(body).strip()



def _bullet_values(section_body: str) -> list[str]:
    values: list[str] = []
    for line in section_body.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            values.append(stripped[2:].strip().strip("`").strip())
    return values



def _match(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    assert match is not None
    return match.group(1)



def test_machine_control_plane_readme_exposes_active_pack_and_local_mode_requirements() -> None:
    readme = _read(README_PATH)

    assert _bullet_values(_section(readme, "Active Pack")) == [
        "docs/plan/active_PLAN.md",
        "docs/plan/active_STATUS.md",
        "docs/plan/active_WORKSET.md",
    ]
    assert _bullet_values(_section(readme, "Current Active Slice")) == ["PS.RV1"]
    assert _bullet_values(_section(readme, "Intended Handoff")) == ["plan-creator"]
    assert _bullet_values(_section(readme, "Source Pack")) == [
        "docs/plan/warning-agent-warning-plane-production-stability-2026-04-20_PLAN.md",
        "docs/plan/warning-agent-warning-plane-production-stability-2026-04-20_STATUS.md",
        "docs/plan/warning-agent-warning-plane-production-stability-2026-04-20_WORKSET.md",
    ]

    for path in [
        ACTIVE_PLAN_PATH,
        ACTIVE_STATUS_PATH,
        ACTIVE_WORKSET_PATH,
        SOURCE_PLAN_PATH,
        SOURCE_STATUS_PATH,
        SOURCE_WORKSET_PATH,
    ]:
        assert path.exists(), path

    assert "pi-sdk" in readme
    assert "dirty-repo initial-run guard" in readme



def test_machine_pack_is_parser_compatible_and_stage_order_is_serial() -> None:
    active_plan = _read(ACTIVE_PLAN_PATH)
    active_status = _read(ACTIVE_STATUS_PATH)
    active_workset = _read(ACTIVE_WORKSET_PATH)

    active_slice = _match(r"^- active_step:\s+`([^`]+)`$", active_status)
    assert active_slice == "PS.RV1"

    workset_active_stage = _match(r"## Active Stage\s+### `([^`]+)`", active_workset)
    assert workset_active_stage == active_slice

    stage_order = re.findall(r"^- \[[ x]\] `([^`]+)`", _section(active_workset, "Stage Order"), re.MULTILINE)
    assert stage_order[:3] == ["PS.S1a", "PS.S1b", "PS.S2a"]
    assert stage_order[-1] == "PS.RV1"
    assert stage_order.index("PS.S1a") < stage_order.index("PS.S1b") < stage_order.index("PS.S2a")

    for slice_id, owner in [
        ("PS.S2b", "execute-plan"),
        ("PS.RV1", "execution-reality-audit"),
    ]:
        slice_body = _match(rf"#### `{re.escape(slice_id)}`\s+(.*?)(?=\n#### `|\Z)", active_plan)
        assert f"- Owner: `{owner}`" in slice_body
        assert "- State: `READY`" in slice_body
        assert "- Priority: `" in slice_body
        assert "目标：" in slice_body
        assert "交付物：" in slice_body
        assert "必须避免：" in slice_body

    assert "## Immediate Focus" in active_status
    assert "## Machine State" in active_status
    assert "## Machine Queue" in active_workset



def test_machine_pack_mirrors_current_source_pack_active_truth() -> None:
    readme = _read(README_PATH)
    active_status = _read(ACTIVE_STATUS_PATH)
    source_workset = _read(SOURCE_WORKSET_PATH)

    machine_active_slice = _bullet_values(_section(readme, "Current Active Slice"))[0]
    machine_active_step = _match(r"^- active_step:\s+`([^`]+)`$", active_status)
    source_active_slice = _match(r"^- active_slice:\s+`([^`]+)`$", source_workset)

    assert machine_active_slice == "PS.RV1"
    assert machine_active_step == machine_active_slice
    assert source_active_slice.startswith(machine_active_slice)
    assert "PS.RV1" in source_workset
