# warning-agent Plan Control Plane

## Active Pack

- `docs/plan/active_PLAN.md`
- `docs/plan/active_STATUS.md`
- `docs/plan/active_WORKSET.md`

## Current Active Slice

- `PS.RV1`

## Intended Handoff

- `plan-creator`

## Source Pack

- `docs/plan/warning-agent-warning-plane-production-stability-2026-04-20_PLAN.md`
- `docs/plan/warning-agent-warning-plane-production-stability-2026-04-20_STATUS.md`
- `docs/plan/warning-agent-warning-plane-production-stability-2026-04-20_WORKSET.md`

## Notes

This `README.md` plus `active_PLAN.md`, `active_STATUS.md`, and `active_WORKSET.md` is the repo-local machine control-plane for `pi-sdk` local autopilot.

It intentionally mirrors the richer warning-plane production-stability source pack above instead of replacing it. If the machine pack and the source pack diverge, update the machine pack first before starting `/autopilot-run` in local mode.

This active pack supersedes the terminal MM machine truth for new execution. It is now in terminal closeout truth at `PS.RV1`, with verdict `accept_with_residuals` and next handoff `plan-creator`.

Local extension mode still has a clean-start requirement: the first `/autopilot-run` in a new local autopilot session should start from a clean repo state, otherwise the dirty-repo initial-run guard is expected to halt before the first dispatch.
