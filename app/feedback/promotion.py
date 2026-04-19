"""Promotion report and gated decision helpers for warning-agent W4."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final, TypedDict

from app.feedback.governance import FeedbackGovernanceConfig, load_feedback_governance_config

DEFAULT_PROMOTION_DECISION_PATH: Final = Path("data/decisions/local-analyzer-promotion-decision.json")
DEFAULT_PROMOTION_REPORT_PATH: Final = Path("data/reports/local-analyzer-promotion-report.md")
DEFAULT_GOVERNANCE_CONFIG_PATH: Final = Path("configs/feedback-governance.yaml")


class PromotionDecision(TypedDict):
    decision_version: str
    compare_summary_path: str
    generated_at: str
    final_decision: str
    candidate_artifact_path: str
    current_analyzer_version: str
    candidate_analyzer_version: str
    rationale: list[str]


def load_compare_summary(path: str | Path) -> dict[str, object]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _decision_from_summary(
    summary: dict[str, object],
    *,
    compare_summary_path: Path,
    governance: FeedbackGovernanceConfig,
) -> PromotionDecision:
    corpus_contract = summary["corpus_contract"]
    candidate = summary["models"]["candidate_retrained"]
    current = summary["models"]["current_runtime"]
    provisional = summary["provisional_decision"]

    landed_outcomes = int(corpus_contract["landed_outcome_case_count"])
    final_decision = "hold_current"
    rationale: list[str] = []
    if landed_outcomes < governance.promotion.minimum_landed_outcome_cases:
        rationale.append("landed_outcome_cases_below_promotion_minimum")
    if provisional["preferred_model"] != "candidate_ready_for_review":
        rationale.append("candidate_not_preferred_by_compare_summary")
    if governance.promotion.auto_promote:
        rationale.append("config_auto_promote_enabled")
    else:
        rationale.append("config_auto_promote_disabled")
    if not rationale or rationale == ["config_auto_promote_disabled"]:
        final_decision = "promote_candidate"
        rationale.append("candidate_cleared_compare_review_rule")

    return {
        "decision_version": "local-analyzer-promotion-decision.v1",
        "compare_summary_path": str(compare_summary_path),
        "generated_at": str(summary["generated_at"]),
        "final_decision": final_decision,
        "candidate_artifact_path": str(candidate["artifact_path"]),
        "current_analyzer_version": str(current["analyzer_version"]),
        "candidate_analyzer_version": str(candidate["analyzer_version"]),
        "rationale": rationale,
    }


def render_promotion_report(summary: dict[str, object], decision: PromotionDecision) -> str:
    candidate = summary["models"]["candidate_retrained"]
    current = summary["models"]["current_runtime"]
    corpus_contract = summary["corpus_contract"]

    return "\n".join(
        [
            "# warning-agent local analyzer promotion review",
            "",
            f"- compare summary: `{decision['compare_summary_path']}`",
            f"- current analyzer: `{decision['current_analyzer_version']}`",
            f"- candidate analyzer: `{decision['candidate_analyzer_version']}`",
            f"- final decision: `{decision['final_decision']}`",
            "",
            "## Corpus contract",
            f"- replay cases: `{corpus_contract['replay_case_count']}`",
            f"- landed outcomes: `{corpus_contract['landed_outcome_case_count']}`",
            f"- total cases: `{corpus_contract['total_cases']}`",
            "",
            "## Current runtime metrics",
            f"- severe recall: `{current['metrics']['severe_recall']}`",
            f"- investigation precision: `{current['metrics']['investigation_precision']}`",
            f"- brier score: `{current['metrics']['brier_score']}`",
            "",
            "## Candidate metrics",
            f"- severe recall: `{candidate['metrics']['severe_recall']}`",
            f"- investigation precision: `{candidate['metrics']['investigation_precision']}`",
            f"- brier score: `{candidate['metrics']['brier_score']}`",
            f"- candidate artifact path: `{candidate['artifact_path']}`",
            "",
            "## Decision rationale",
            *[f"- {reason}" for reason in decision["rationale"]],
            "",
            "## Notes",
            "- no automatic promotion occurred without an explicit decision artifact",
            "- governance freeze and rollback policy remain a separate W4 step",
        ]
    ) + "\n"


def run_feedback_promotion_review(
    *,
    compare_summary_path: str | Path,
    decision_output_path: str | Path = DEFAULT_PROMOTION_DECISION_PATH,
    report_output_path: str | Path = DEFAULT_PROMOTION_REPORT_PATH,
    config_path: str | Path = DEFAULT_GOVERNANCE_CONFIG_PATH,
    repo_root: Path = Path("."),
) -> tuple[PromotionDecision, str]:
    repo_root = Path(repo_root)
    compare_summary_path = Path(compare_summary_path)
    if not compare_summary_path.is_absolute():
        compare_summary_path = repo_root / compare_summary_path

    summary = load_compare_summary(compare_summary_path)
    resolved_config_path = Path(config_path)
    if not resolved_config_path.is_absolute():
        resolved_config_path = repo_root / resolved_config_path
    governance = load_feedback_governance_config(resolved_config_path)
    decision = _decision_from_summary(
        summary,
        compare_summary_path=compare_summary_path,
        governance=governance,
    )
    report = render_promotion_report(summary, decision)

    decision_output_path = Path(decision_output_path)
    if not decision_output_path.is_absolute():
        decision_output_path = repo_root / decision_output_path
    report_output_path = Path(report_output_path)
    if not report_output_path.is_absolute():
        report_output_path = repo_root / report_output_path

    decision_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_output_path.parent.mkdir(parents=True, exist_ok=True)
    decision_output_path.write_text(json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_output_path.write_text(report, encoding="utf-8")
    return decision, report
