"""External outcome admission API surface for warning-agent."""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.feedback.outcome_ingest import OutcomeIngestRequest, ingest_incident_outcome
from app.feedback.retrieval_refresh import refresh_outcome_retrieval_docs
from app.retrieval.index import RetrievalIndex
from app.storage.artifact_store import JSONLArtifactStore
from app.storage.sqlite_store import MetadataStore

RECEIPT_SCHEMA_VERSION: str = "outcome-admission-receipt.v1"


class OutcomeAdmissionError(TypedDict):
    code: str
    message: str


class OutcomeAdmissionReceipt(TypedDict):
    schema_version: str
    admitted: bool
    receipt_state: Literal["admitted", "rejected"]
    outcome_id: str | None
    artifact_path: str | None
    metadata_db_path: str | None
    metadata_artifact_id: str | None
    retrieval_refreshed: bool
    retrieval_refreshed_count: int
    retrieval_refreshed_doc_ids: list[str]
    retrieval_db_path: str | None
    error: NotRequired[OutcomeAdmissionError]


class OutcomeAdmissionRequest(BaseModel):
    source: Literal["operator", "replay_label", "postmortem"]
    recorded_at: str
    service: str
    operation: str | None = None
    environment: str
    packet_id: str
    decision_id: str
    investigation_id: str | None = None
    report_id: str | None = None
    known_outcome: str
    final_severity_band: str
    final_recommended_action: str
    resolution_summary: str
    notes: list[str] = Field(default_factory=list)
    evidence_links: dict[str, str] | None = None


def _build_error_receipt(code: str, message: str) -> OutcomeAdmissionReceipt:
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "admitted": False,
        "receipt_state": "rejected",
        "outcome_id": None,
        "artifact_path": None,
        "metadata_db_path": None,
        "metadata_artifact_id": None,
        "retrieval_refreshed": False,
        "retrieval_refreshed_count": 0,
        "retrieval_refreshed_doc_ids": [],
        "retrieval_db_path": None,
        "error": {"code": code, "message": message},
    }


def build_outcome_router(
    artifact_store: JSONLArtifactStore,
    metadata_store: MetadataStore | None = None,
    retrieval_index: RetrievalIndex | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/outcome")

    @router.post("/admit", response_model=None)
    def admit_outcome(request: OutcomeAdmissionRequest) -> OutcomeAdmissionReceipt | JSONResponse:
        try:
            ingest_request = OutcomeIngestRequest(
                source=request.source,
                recorded_at=request.recorded_at,
                service=request.service,
                operation=request.operation,
                environment=request.environment,
                packet_id=request.packet_id,
                decision_id=request.decision_id,
                investigation_id=request.investigation_id,
                report_id=request.report_id,
                known_outcome=request.known_outcome,
                final_severity_band=request.final_severity_band,
                final_recommended_action=request.final_recommended_action,
                resolution_summary=request.resolution_summary,
                notes=tuple(request.notes),
                evidence_links=request.evidence_links,
            )
            receipt = ingest_incident_outcome(
                ingest_request,
                artifact_store=artifact_store,
                metadata_store=metadata_store,
            )
            refresh_result = refresh_outcome_retrieval_docs(
                artifact_store=artifact_store,
                retrieval_index=retrieval_index,
            )
            return {
                "schema_version": RECEIPT_SCHEMA_VERSION,
                "admitted": True,
                "receipt_state": "admitted",
                "outcome_id": receipt.outcome["outcome_id"],
                "artifact_path": str(receipt.persisted.artifact_path),
                "metadata_db_path": str(receipt.persisted.metadata_db_path),
                "metadata_artifact_id": receipt.outcome["outcome_id"],
                "retrieval_refreshed": True,
                "retrieval_refreshed_count": refresh_result.refreshed_count,
                "retrieval_refreshed_doc_ids": list(refresh_result.refreshed_doc_ids),
                "retrieval_db_path": refresh_result.retrieval_db_path,
            }
        except ValueError as exc:
            return JSONResponse(
                status_code=422,
                content=_build_error_receipt("schema_validation_error", str(exc)),
            )
        except Exception as exc:
            return JSONResponse(
                status_code=500,
                content=_build_error_receipt("internal_error", str(exc)),
            )

    return router


def register_outcome_exception_handlers(app: FastAPI) -> None:
    from fastapi.exception_handlers import request_validation_exception_handler

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(request, exc: RequestValidationError) -> JSONResponse:
        if request.url.path.startswith("/outcome"):
            message = "; ".join(
                f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
                for err in exc.errors()
            )
            return JSONResponse(
                status_code=422,
                content=_build_error_receipt("validation_error", message),
            )
        return await request_validation_exception_handler(request, exc)
