from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

import app
from app.main import RuntimeEntrypoint, build_runtime_entrypoint, get_app_metadata
from app.retrieval.index import RetrievalIndex
from app.retrieval.search import search_documents
from app.storage.artifact_store import JSONLArtifactStore
from app.storage.sqlite_store import MetadataStore


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE = REPO_ROOT / "fixtures" / "replay" / "manual-replay.checkout.high-error-rate.json"
CURRENT_STATUS = REPO_ROOT / "docs" / "plan" / "warning-agent-architecture-clarity-optimization-2026-04-20_STATUS.md"
CURRENT_WORKSET = REPO_ROOT / "docs" / "plan" / "warning-agent-architecture-clarity-optimization-2026-04-20_WORKSET.md"



def _read_plan_header_value(path: Path, key: str) -> str:
    marker = f"- {key}: `"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(marker) and line.endswith("`"):
            return line[len(marker) : -1]
    raise AssertionError(f"missing {key} in {path}")



def test_pyproject_metadata_matches_package() -> None:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)

    metadata = get_app_metadata()

    assert pyproject["project"]["name"] == "warning-agent"
    assert pyproject["project"]["scripts"]["warning-agent"] == "app.main:main"
    assert metadata.name == "warning-agent"
    assert metadata.version == app.__version__
    assert metadata.phase == "architecture-clarity-optimization"
    assert metadata.active_slice == _read_plan_header_value(CURRENT_WORKSET, "active_slice")
    assert _read_plan_header_value(CURRENT_STATUS, "status") in {"ready", "in_progress", "completed"}



def test_build_runtime_entrypoint_creates_replay_first_contract() -> None:
    entrypoint = build_runtime_entrypoint(
        ["replay", "fixtures/replay/manual-replay.checkout.high-error-rate.json"],
        cwd=REPO_ROOT,
    )

    assert entrypoint == RuntimeEntrypoint(
        mode="replay",
        replay_fixture=REPLAY_FIXTURE,
        candidate_source="manual_replay",
    )


@pytest.mark.parametrize(
    ("argv", "error_text"),
    [
        ([], "usage:"),
        (["replay"], "replay mode requires a fixture path"),
        (["replay", "fixtures/replay/does-not-exist.json"], "replay fixture does not exist"),
    ],
)
def test_build_runtime_entrypoint_rejects_invalid_cli_shapes(argv: list[str], error_text: str) -> None:
    with pytest.raises(ValueError, match=error_text):
        build_runtime_entrypoint(argv, cwd=REPO_ROOT)



def _assert_replay_runtime_artifacts(tmp_path: Path, stdout: str) -> None:
    store = JSONLArtifactStore(root=tmp_path)
    metadata_store = MetadataStore(db_path=tmp_path / "metadata.sqlite3")
    retrieval_index = RetrievalIndex(db_path=tmp_path / "retrieval" / "retrieval.sqlite3")

    assert "warning-agent replay runtime executed" in stdout
    assert "packet_id=ipk_checkout_post_api_pay_20260418t120008z" in stdout
    assert "decision_id=lad_checkout_post_pay_20260418t120010z" in stdout
    assert "investigation_stage=cloud_fallback" in stdout
    assert "## Executive Summary" in stdout
    assert [record["packet_id"] for record in store.read_all("packets")] == ["ipk_checkout_post_api_pay_20260418t120008z"]
    assert [record["decision_id"] for record in store.read_all("decisions")] == ["lad_checkout_post_pay_20260418t120010z"]
    assert [record["report_id"] for record in store.read_all("reports")] == ["rpt_checkout_post_api_pay_20260418t120008z"]
    assert [record["artifact_id"] for record in metadata_store.list_artifacts("alert_reports")] == [
        "rpt_checkout_post_api_pay_20260418t120008z"
    ]
    assert {hit.doc_id for hit in search_documents(retrieval_index, "timeout", service="checkout")} >= {
        "rpt_checkout_post_api_pay_20260418t120008z"
    }



def test_cli_entrypoint_executes_replay_runtime_path_and_persists_artifacts(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["WARNING_AGENT_DATA_DIR"] = str(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.main",
            "replay",
            "fixtures/replay/manual-replay.checkout.high-error-rate.json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    _assert_replay_runtime_artifacts(tmp_path, result.stdout)



def test_pyproject_declares_expected_runtime_dependencies() -> None:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)

    dependencies = set(pyproject["project"]["dependencies"])
    assert any(dep.startswith("fastapi>=") for dep in dependencies)
    assert any(dep.startswith("uvicorn>=") for dep in dependencies)
    assert any(dep.startswith("pydantic>=") for dep in dependencies)



def test_repo_root_contains_expected_runtime_layout() -> None:
    assert (REPO_ROOT / "app").is_dir()
    assert (REPO_ROOT / "schemas").is_dir()
    assert (REPO_ROOT / "configs").is_dir()
    assert (REPO_ROOT / "tests").is_dir()



def test_python_compileall_succeeds_for_app_package(tmp_path: Path) -> None:
    compile_root = tmp_path / "compileall"
    shutil.copytree(REPO_ROOT / "app", compile_root / "app")

    subprocess.run(
        [sys.executable, "-m", "compileall", str(compile_root / "app")],
        check=True,
        capture_output=True,
        text=True,
    )



def test_runtime_control_plane_files_exist() -> None:
    assert CURRENT_STATUS.exists()
    assert CURRENT_WORKSET.exists()
