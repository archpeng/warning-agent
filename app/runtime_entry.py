"""Replay-first runtime execution helpers for warning-agent."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from app.analyzer.base import load_thresholds
from app.analyzer.runtime import resolve_runtime_scorer
from app.collectors.evidence_bundle import build_live_evidence_bundle, build_signoz_first_evidence_bundle
from app.delivery.runtime import persist_report_delivery
from app.collectors.prometheus import PrometheusCollector
from app.collectors.signoz import SignozCollector
from app.integration_evidence import persist_integration_rollout_evidence
from app.investigator.runtime import run_investigation_runtime
from app.packet.builder import build_incident_packet_from_bundle
from app.receiver.alertmanager_webhook import normalize_alertmanager_payload
from app.receiver.replay_loader import load_manual_replay_fixture
from app.receiver.signoz_alert import normalize_signoz_alert_payload
from app.reports.markdown_builder import render_alert_report
from app.retrieval.index import RetrievalIndex
from app.retrieval.search import search_labeled_outcomes
from app.storage.artifact_store import JSONLArtifactStore
from app.storage.sqlite_store import MetadataStore


RUNTIME_RETRIEVAL_TOKEN_PATTERN = re.compile(r"[a-z0-9]{3,}")
RUNTIME_RETRIEVAL_LIMIT = 3


EvidenceSource = Literal["fixture", "live"]


@dataclass(frozen=True)
class RuntimeEntrypoint:
    mode: Literal["replay", "signoz_alert"]
    replay_fixture: Path
    candidate_source: Literal["manual_replay", "signoz_alert"] = "manual_replay"
    evidence_source: EvidenceSource = "fixture"


@dataclass(frozen=True)
class PersistedRuntimeArtifacts:
    packet_path: Path
    decision_path: Path
    investigation_path: Path | None
    report_path: Path
    delivery_dispatches_path: Path | None = None
    metadata_db_path: Path | None = None
    retrieval_db_path: Path | None = None
    rollout_evidence_path: Path | None = None


@dataclass(frozen=True)
class ReplayRuntimeExecution:
    entrypoint: RuntimeEntrypoint | None
    evidence_fixture: Path | None
    normalized_alert: dict[str, object]
    packet: dict[str, object]
    decision: dict[str, object]
    investigation: dict[str, object] | None
    report: str
    persisted_artifacts: PersistedRuntimeArtifacts | None = None


@dataclass(frozen=True)
class RuntimeExecutionSummary:
    packet_id: str
    decision_id: str
    investigation_id: str | None
    investigation_stage: Literal["none", "local_primary", "cloud_fallback"]
    report_id: str
    rollout_evidence_path: str | None = None


def build_runtime_execution_summary(execution: ReplayRuntimeExecution) -> RuntimeExecutionSummary:
    report_record = _build_report_artifact_record(execution.report)
    investigation_stage: Literal["none", "local_primary", "cloud_fallback"] = "none"
    investigation_id = None
    if execution.investigation is not None:
        investigation_id = str(execution.investigation["investigation_id"])
        investigation_stage = (
            "cloud_fallback"
            if execution.investigation["investigator_tier"] == "cloud_fallback_investigator"
            else "local_primary"
        )

    rollout_evidence_path = None
    if execution.persisted_artifacts is not None and execution.persisted_artifacts.rollout_evidence_path is not None:
        rollout_evidence_path = str(execution.persisted_artifacts.rollout_evidence_path)

    return RuntimeExecutionSummary(
        packet_id=str(execution.packet["packet_id"]),
        decision_id=str(execution.decision["decision_id"]),
        investigation_id=investigation_id,
        investigation_stage=investigation_stage,
        report_id=str(report_record["report_id"]),
        rollout_evidence_path=rollout_evidence_path,
    )


def resolve_replay_evidence_fixture(
    entrypoint: RuntimeEntrypoint,
    *,
    repo_root: str | Path = Path("."),
) -> Path:
    repo_root = Path(repo_root)
    replay = load_manual_replay_fixture(entrypoint.replay_fixture)
    normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")
    service = normalized.get("service")
    if not service:
        raise ValueError("replay fixture must normalize to a service before runtime execution")

    evidence_fixture = (repo_root / "fixtures" / "evidence" / f"{service}.packet-input.json").resolve()
    if not evidence_fixture.exists():
        raise ValueError(f"replay evidence fixture does not exist: {evidence_fixture}")
    return evidence_fixture


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _build_report_artifact_record(report: str) -> dict[str, object]:
    report_parts = report.split("---", maxsplit=2)
    if len(report_parts) != 3:
        raise ValueError("alert report must contain frontmatter before artifact writeback")

    _, frontmatter_block, _ = report_parts
    frontmatter = yaml.safe_load(frontmatter_block)
    if not isinstance(frontmatter, dict):
        raise ValueError("alert report frontmatter must parse to a mapping before artifact writeback")

    return {
        **frontmatter,
        "markdown": report,
    }


def _build_metadata_store(artifact_store: JSONLArtifactStore) -> MetadataStore:
    return MetadataStore(db_path=artifact_store.root / "metadata.sqlite3")


def _build_retrieval_index(artifact_store: JSONLArtifactStore) -> RetrievalIndex:
    return RetrievalIndex(db_path=artifact_store.root / "retrieval" / "retrieval.sqlite3")



def _tokenize_runtime_retrieval_query(packet: dict[str, object]) -> list[str]:
    signoz = packet.get("signoz") or {}
    if not isinstance(signoz, dict):
        signoz = {}

    tokens: list[str] = []
    top_error_templates = signoz.get("top_error_templates") or []
    if isinstance(top_error_templates, list):
        for template in top_error_templates[:2]:
            if not isinstance(template, dict):
                continue
            body = str(template.get("body") or "").lower()
            tokens.extend(RUNTIME_RETRIEVAL_TOKEN_PATTERN.findall(body))

    operation = str(packet.get("operation") or "").lower()
    tokens.extend(RUNTIME_RETRIEVAL_TOKEN_PATTERN.findall(operation))

    unique_tokens: list[str] = []
    for token in tokens:
        if token not in unique_tokens:
            unique_tokens.append(token)
    return unique_tokens[:8]



def _build_runtime_retrieval_query(packet: dict[str, object]) -> str:
    tokens = _tokenize_runtime_retrieval_query(packet)
    if tokens:
        return " OR ".join(tokens)
    return str(packet["service"])



def _resolve_runtime_retrieval_index(
    *,
    repo_root: Path,
    artifact_store: JSONLArtifactStore | None,
    retrieval_index: RetrievalIndex | None,
) -> RetrievalIndex:
    if retrieval_index is not None:
        return retrieval_index
    if artifact_store is not None:
        return _build_retrieval_index(artifact_store)
    return RetrievalIndex(db_path=repo_root / "data" / "retrieval" / "retrieval.sqlite3")



def _resolve_runtime_retrieval_hits(packet: dict[str, object], *, retrieval_index: RetrievalIndex) -> list[dict[str, object]]:
    retrieval_index.initialize()
    return list(
        search_labeled_outcomes(
            retrieval_index,
            _build_runtime_retrieval_query(packet),
            service=str(packet["service"]),
            limit=RUNTIME_RETRIEVAL_LIMIT,
        )
    )



def _record_runtime_metadata(
    execution: ReplayRuntimeExecution,
    *,
    report_record: dict[str, object],
    persisted_artifacts: PersistedRuntimeArtifacts,
    metadata_store: MetadataStore,
) -> None:
    metadata_store.initialize()
    metadata_store.record_artifact(
        "packets",
        artifact_id=str(execution.packet["packet_id"]),
        schema_version=str(execution.packet["schema_version"]),
        artifact_path=str(persisted_artifacts.packet_path),
        service=str(execution.packet["service"]),
        operation=str(execution.packet.get("operation") or ""),
        created_at=str(execution.packet["created_at"]),
    )
    metadata_store.record_artifact(
        "local_decisions",
        artifact_id=str(execution.decision["decision_id"]),
        schema_version=str(execution.decision["schema_version"]),
        artifact_path=str(persisted_artifacts.decision_path),
        service=str(execution.packet["service"]),
        operation=str(execution.packet.get("operation") or ""),
        created_at=str(execution.packet["created_at"]),
    )
    if execution.investigation is not None and persisted_artifacts.investigation_path is not None:
        metadata_store.record_artifact(
            "investigations",
            artifact_id=str(execution.investigation["investigation_id"]),
            schema_version=str(execution.investigation["schema_version"]),
            artifact_path=str(persisted_artifacts.investigation_path),
            service=str(execution.packet["service"]),
            operation=str(execution.packet.get("operation") or ""),
            created_at=str(execution.investigation["generated_at"]),
        )
    metadata_store.record_artifact(
        "alert_reports",
        artifact_id=str(report_record["report_id"]),
        schema_version=str(report_record["schema_version"]),
        artifact_path=str(persisted_artifacts.report_path),
        service=str(report_record["service"]),
        operation=str(report_record.get("operation") or ""),
        created_at=str(report_record["generated_at"]),
    )


def _upsert_runtime_retrieval_docs(
    execution: ReplayRuntimeExecution,
    *,
    report_record: dict[str, object],
    retrieval_index: RetrievalIndex,
) -> None:
    retrieval_index.initialize()
    service = str(execution.packet["service"])
    operation = str(execution.packet.get("operation") or "")
    retrieval_index.upsert_document(
        doc_id=str(execution.packet["packet_id"]),
        kind="packet",
        service=service,
        operation=operation,
        body=json.dumps(execution.packet, ensure_ascii=False, sort_keys=True),
    )
    retrieval_index.upsert_document(
        doc_id=str(execution.decision["decision_id"]),
        kind="local_decision",
        service=service,
        operation=operation,
        body=json.dumps(execution.decision, ensure_ascii=False, sort_keys=True),
    )
    if execution.investigation is not None:
        retrieval_index.upsert_document(
            doc_id=str(execution.investigation["investigation_id"]),
            kind="investigation",
            service=service,
            operation=operation,
            body=json.dumps(execution.investigation, ensure_ascii=False, sort_keys=True),
        )
    retrieval_index.upsert_document(
        doc_id=str(report_record["report_id"]),
        kind="alert_report",
        service=service,
        operation=operation,
        body=execution.report,
    )


def persist_runtime_execution(
    execution: ReplayRuntimeExecution,
    *,
    artifact_store: JSONLArtifactStore,
    repo_root: str | Path = Path("."),
    metadata_store: MetadataStore | None = None,
    retrieval_index: RetrievalIndex | None = None,
    delivery_config_path: str | Path = Path("configs/delivery.yaml"),
) -> PersistedRuntimeArtifacts:
    packet_path = artifact_store.append("packets", execution.packet)
    decision_path = artifact_store.append("decisions", execution.decision)
    investigation_path = None
    if execution.investigation is not None:
        investigation_path = artifact_store.append("investigations", execution.investigation)
    report_record = _build_report_artifact_record(execution.report)
    report_path = artifact_store.append("reports", report_record)

    delivery_dispatch = persist_report_delivery(
        report_record=report_record,
        artifact_store=artifact_store,
        config_path=delivery_config_path,
    )

    rollout_evidence_path = persist_integration_rollout_evidence(
        artifact_root=artifact_store.root,
        repo_root=repo_root,
        data_root=artifact_store.root,
        packet_id=str(execution.packet["packet_id"]),
        decision_id=str(execution.decision["decision_id"]),
        report_id=str(report_record["report_id"]),
        generated_at=str(report_record["generated_at"]),
    )

    persisted_artifacts = PersistedRuntimeArtifacts(
        packet_path=packet_path,
        decision_path=decision_path,
        investigation_path=investigation_path,
        report_path=report_path,
        delivery_dispatches_path=delivery_dispatch.dispatch_path,
        rollout_evidence_path=rollout_evidence_path,
    )
    metadata_store = metadata_store or _build_metadata_store(artifact_store)
    retrieval_index = retrieval_index or _build_retrieval_index(artifact_store)
    _record_runtime_metadata(
        execution,
        report_record=report_record,
        persisted_artifacts=persisted_artifacts,
        metadata_store=metadata_store,
    )
    _upsert_runtime_retrieval_docs(
        execution,
        report_record=report_record,
        retrieval_index=retrieval_index,
    )
    return PersistedRuntimeArtifacts(
        packet_path=packet_path,
        decision_path=decision_path,
        investigation_path=investigation_path,
        report_path=report_path,
        delivery_dispatches_path=delivery_dispatch.dispatch_path,
        metadata_db_path=metadata_store.db_path,
        retrieval_db_path=retrieval_index.db_path,
        rollout_evidence_path=rollout_evidence_path,
    )


def resolve_runtime_evidence_bundle(
    entrypoint: RuntimeEntrypoint,
    *,
    normalized_alert: dict[str, object],
    repo_root: str | Path = Path("."),
    prometheus_collector: PrometheusCollector | None = None,
    signoz_collector: SignozCollector | None = None,
    evidence_now: str | None = None,
) -> tuple[Path | None, dict[str, object]]:
    repo_root = Path(repo_root)
    if entrypoint.candidate_source == "signoz_alert":
        return (
            None,
            build_signoz_first_evidence_bundle(
                normalized_alert,  # type: ignore[arg-type]
                repo_root=repo_root,
                prometheus_collector=prometheus_collector,
                signoz_collector=signoz_collector,
                now=evidence_now,
            ),
        )

    if entrypoint.evidence_source == "fixture":
        evidence_fixture = resolve_replay_evidence_fixture(entrypoint, repo_root=repo_root)
        return evidence_fixture, _load_json(evidence_fixture)

    return (
        None,
        build_live_evidence_bundle(
            normalized_alert,  # type: ignore[arg-type]
            repo_root=repo_root,
            prometheus_collector=prometheus_collector,
            signoz_collector=signoz_collector,
            now=evidence_now,
        ),
    )


def execute_runtime_inputs(
    *,
    normalized_alert: dict[str, object],
    evidence_bundle: dict[str, object],
    repo_root: str | Path = Path("."),
    entrypoint: RuntimeEntrypoint | None = None,
    evidence_fixture: Path | None = None,
    artifact_store: JSONLArtifactStore | None = None,
    metadata_store: MetadataStore | None = None,
    retrieval_index: RetrievalIndex | None = None,
    persist_artifacts: bool = True,
) -> ReplayRuntimeExecution:
    repo_root = Path(repo_root)
    packet = build_incident_packet_from_bundle(normalized_alert, evidence_bundle)
    runtime_retrieval_index = _resolve_runtime_retrieval_index(
        repo_root=repo_root,
        artifact_store=artifact_store,
        retrieval_index=retrieval_index,
    )
    runtime_retrieval_hits = _resolve_runtime_retrieval_hits(packet, retrieval_index=runtime_retrieval_index)
    decision = resolve_runtime_scorer(
        repo_root=repo_root,
        thresholds=load_thresholds(repo_root / "configs" / "thresholds.yaml"),
    ).score_packet(
        packet,
        retrieval_hits=runtime_retrieval_hits,
    )
    investigation = None
    if decision["needs_investigation"]:
        execution = run_investigation_runtime(
            packet,
            decision,
            config_path=repo_root / "configs" / "escalation.yaml",
            repo_root=repo_root,
        )
        investigation = execution.final_result

    report = render_alert_report(packet, decision, investigation)
    runtime_execution = ReplayRuntimeExecution(
        entrypoint=entrypoint,
        evidence_fixture=evidence_fixture,
        normalized_alert=normalized_alert,
        packet=packet,
        decision=decision,
        investigation=investigation,
        report=report,
    )
    if not persist_artifacts:
        return runtime_execution

    artifact_store = artifact_store or JSONLArtifactStore()
    persisted_artifacts = persist_runtime_execution(
        runtime_execution,
        artifact_store=artifact_store,
        repo_root=repo_root,
        metadata_store=metadata_store,
        retrieval_index=runtime_retrieval_index,
        delivery_config_path=repo_root / "configs" / "delivery.yaml",
    )
    return ReplayRuntimeExecution(
        entrypoint=runtime_execution.entrypoint,
        evidence_fixture=runtime_execution.evidence_fixture,
        normalized_alert=runtime_execution.normalized_alert,
        packet=runtime_execution.packet,
        decision=runtime_execution.decision,
        investigation=runtime_execution.investigation,
        report=runtime_execution.report,
        persisted_artifacts=persisted_artifacts,
    )



def execute_runtime_entrypoint(
    entrypoint: RuntimeEntrypoint,
    *,
    repo_root: str | Path = Path("."),
    artifact_store: JSONLArtifactStore | None = None,
    metadata_store: MetadataStore | None = None,
    retrieval_index: RetrievalIndex | None = None,
    persist_artifacts: bool = True,
    prometheus_collector: PrometheusCollector | None = None,
    signoz_collector: SignozCollector | None = None,
    evidence_now: str | None = None,
) -> ReplayRuntimeExecution:
    repo_root = Path(repo_root)
    if entrypoint.mode == "signoz_alert":
        normalized = normalize_signoz_alert_payload(_load_json(entrypoint.replay_fixture))
    else:
        replay = load_manual_replay_fixture(entrypoint.replay_fixture)
        normalized = normalize_alertmanager_payload(replay["alert_payload"], candidate_source="manual_replay")

    evidence_fixture, evidence_bundle = resolve_runtime_evidence_bundle(
        entrypoint,
        normalized_alert=normalized,
        repo_root=repo_root,
        prometheus_collector=prometheus_collector,
        signoz_collector=signoz_collector,
        evidence_now=evidence_now,
    )

    return execute_runtime_inputs(
        normalized_alert=normalized,
        evidence_bundle=evidence_bundle,
        repo_root=repo_root,
        entrypoint=entrypoint,
        evidence_fixture=evidence_fixture,
        artifact_store=artifact_store,
        metadata_store=metadata_store,
        retrieval_index=retrieval_index,
        persist_artifacts=persist_artifacts,
    )
