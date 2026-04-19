"""investigator package."""

from app.investigator.base import (
    InvestigationRequest,
    InvestigatorBudget,
    InvestigatorProvider,
    build_investigation_request,
)
from app.investigator.benchmark import evaluate_local_primary_acceptance, run_local_primary_benchmark
from app.investigator.cloud_fallback import (
    CloudFallbackAuditRecord,
    CloudFallbackClientRequest,
    CloudFallbackClientResponse,
    CloudFallbackGuardSnapshot,
    CloudFallbackInvestigator,
    CloudFallbackRequest,
    build_cloud_audit_record,
    build_cloud_client_request,
    build_cloud_fallback_request,
    build_cloud_handoff_markdown,
    build_cloud_unavailable_local_fallback,
    evaluate_cloud_fallback_guards,
    run_cloud_fallback_with_local_fallback,
)
from app.investigator.contracts import InvestigationResult
from app.investigator.fallback import build_degraded_local_fallback, run_local_primary_with_fallback
from app.investigator.local_primary import LocalPrimaryInvestigator, build_investigation_id
from app.investigator.router import (
    CloudFallbackAuditConfig,
    CloudFallbackBudget,
    CloudFallbackConfig,
    CloudFallbackRoutePlan,
    InvestigationRoutePlan,
    InvestigatorRoutingConfig,
    load_investigator_routing_config,
    plan_cloud_fallback,
    plan_investigation,
)
from app.investigator.runtime import InvestigationExecutionTrace, run_investigation_runtime
from app.investigator.tools import (
    BoundedInvestigatorTools,
    RepoSearchHit,
    ToolBudgetExceededError,
    ToolUsageSnapshot,
)

__all__ = [
    "BoundedInvestigatorTools",
    "CloudFallbackAuditConfig",
    "CloudFallbackAuditRecord",
    "CloudFallbackBudget",
    "CloudFallbackClientRequest",
    "CloudFallbackClientResponse",
    "CloudFallbackConfig",
    "CloudFallbackGuardSnapshot",
    "CloudFallbackInvestigator",
    "CloudFallbackRequest",
    "CloudFallbackRoutePlan",
    "InvestigationExecutionTrace",
    "InvestigationRequest",
    "InvestigationResult",
    "InvestigationRoutePlan",
    "InvestigatorBudget",
    "InvestigatorProvider",
    "InvestigatorRoutingConfig",
    "LocalPrimaryInvestigator",
    "RepoSearchHit",
    "ToolBudgetExceededError",
    "ToolUsageSnapshot",
    "build_cloud_audit_record",
    "build_cloud_client_request",
    "build_cloud_fallback_request",
    "build_cloud_handoff_markdown",
    "build_cloud_unavailable_local_fallback",
    "build_degraded_local_fallback",
    "evaluate_local_primary_acceptance",
    "build_investigation_id",
    "build_investigation_request",
    "evaluate_cloud_fallback_guards",
    "load_investigator_routing_config",
    "plan_cloud_fallback",
    "plan_investigation",
    "run_cloud_fallback_with_local_fallback",
    "run_investigation_runtime",
    "run_local_primary_benchmark",
    "run_local_primary_with_fallback",
]
