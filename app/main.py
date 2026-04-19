"""Replay-first runtime entrypoint for warning-agent."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from app import __version__
from app.runtime_entry import RuntimeEntrypoint, build_runtime_execution_summary, execute_runtime_entrypoint
from app.storage.artifact_store import JSONLArtifactStore


DEFAULT_APP_PHASE = "production-readiness-foundation"
DEFAULT_APP_ACTIVE_SLICE = "none"
PLAN_ID_PATTERN = re.compile(r"^warning-agent-(?P<phase>.+)-(?P<date>\d{4}-\d{2}-\d{2})$")


@dataclass(frozen=True)
class AppMetadata:
    name: str
    version: str
    phase: str
    active_slice: str


def _parse_plan_header_value(path: Path, key: str) -> str | None:
    marker = f"- {key}: `"
    if not path.exists():
        return None

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(marker) and line.endswith("`"):
            return line[len(marker) : -1]
        if line and not line.startswith("#") and not line.startswith("- "):
            break

    return None



def _load_control_plane_metadata(repo_root: Path | None = None) -> AppMetadata | None:
    plan_root = (repo_root or Path(__file__).resolve().parents[1]) / "docs" / "plan"
    if not plan_root.exists():
        return None

    active_candidates: list[tuple[str, AppMetadata]] = []
    completed_candidates: list[tuple[str, AppMetadata]] = []
    for status_path in plan_root.glob("*_STATUS.md"):
        status = _parse_plan_header_value(status_path, "status")
        plan_id = _parse_plan_header_value(status_path, "plan_id")
        if not plan_id:
            continue

        match = PLAN_ID_PATTERN.match(plan_id)
        if not match:
            continue

        workset_path = status_path.with_name(status_path.name.replace("_STATUS.md", "_WORKSET.md"))
        active_slice = _parse_plan_header_value(workset_path, "active_slice") or DEFAULT_APP_ACTIVE_SLICE
        metadata = AppMetadata(
            name="warning-agent",
            version=__version__,
            phase=match.group("phase"),
            active_slice=active_slice,
        )
        candidate = (match.group("date"), metadata)
        if status == "completed":
            completed_candidates.append(candidate)
        else:
            active_candidates.append(candidate)

    if active_candidates:
        return max(active_candidates, key=lambda item: item[0])[1]
    if completed_candidates:
        return max(completed_candidates, key=lambda item: item[0])[1]
    return None



def get_app_metadata() -> AppMetadata:
    metadata = _load_control_plane_metadata()
    if metadata is not None:
        return metadata

    return AppMetadata(
        name="warning-agent",
        version=__version__,
        phase=DEFAULT_APP_PHASE,
        active_slice=DEFAULT_APP_ACTIVE_SLICE,
    )


def _usage() -> str:
    return "usage: warning-agent replay [--live] <fixture-path> | warning-agent signoz-alert <fixture-path>"


def build_runtime_entrypoint(
    argv: Sequence[str] | None = None,
    *,
    cwd: str | Path | None = None,
) -> RuntimeEntrypoint:
    args = list(argv or [])
    base_dir = Path(cwd or Path.cwd())

    if not args:
        raise ValueError(_usage())
    if args[0] not in {"replay", "signoz-alert"}:
        raise ValueError(_usage())
    mode = args[0]
    trailing = list(args[1:])
    live_mode = False
    if "--live" in trailing:
        live_mode = True
        trailing = [arg for arg in trailing if arg != "--live"]

    if len(trailing) < 1:
        raise ValueError(f"{mode} mode requires a fixture path")
    if len(trailing) > 1:
        raise ValueError("replay mode accepts exactly one fixture path")

    replay_fixture = Path(trailing[0])
    if not replay_fixture.is_absolute():
        replay_fixture = (base_dir / replay_fixture).resolve()
    if not replay_fixture.exists():
        raise ValueError(f"replay fixture does not exist: {replay_fixture}")

    if mode == "signoz-alert":
        return RuntimeEntrypoint(
            mode="signoz_alert",
            replay_fixture=replay_fixture,
            candidate_source="signoz_alert",
            evidence_source="live",
        )

    return RuntimeEntrypoint(
        mode="replay",
        replay_fixture=replay_fixture,
        evidence_source="live" if live_mode else "fixture",
    )


def _resolve_artifact_store() -> JSONLArtifactStore:
    root = os.environ.get("WARNING_AGENT_DATA_DIR")
    return JSONLArtifactStore(root=Path(root)) if root else JSONLArtifactStore()


def _resolve_cli_args(argv: Sequence[str] | None = None) -> list[str]:
    if argv is not None:
        return list(argv)

    import sys

    return list(sys.argv[1:])


def main(argv: Sequence[str] | None = None) -> int:
    try:
        entrypoint = build_runtime_entrypoint(_resolve_cli_args(argv))
        execution = execute_runtime_entrypoint(entrypoint, artifact_store=_resolve_artifact_store())
    except ValueError as exc:
        print(str(exc))
        return 2

    summary = build_runtime_execution_summary(execution)
    print(
        f"warning-agent {entrypoint.mode} runtime executed "
        f"(packet_id={summary.packet_id} decision_id={summary.decision_id} "
        f"investigation_stage={summary.investigation_stage} evidence_source={entrypoint.evidence_source} "
        f"evidence_fixture={execution.evidence_fixture})"
    )
    print()
    print(execution.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
