# Release Note — W6 integration bridge and autopilot control plane

- status: `published-in-repo`
- release_date: `2026-04-20`
- repo: `warning-agent`
- primary_commit: `d5c09d0`
- owner: `repo maintainer`

## 1. Summary

This release lands the current W6 external integration bridge baseline and the repo-local machine control-plane needed for `pi-sdk` local autopilot continuation.

Primary outcomes:

1. external outcome admission surface is now materialized in repo runtime
2. first vendor delivery bridge (`adapter-feishu`) is now present as an env-gated runtime surface
3. provider runtime boundary is now frozen and runtime-gated instead of remaining contract-only
4. repo-local active control-plane now exists under `docs/plan/active_*`
5. local autopilot clean-start policy is now documented as an operator runbook

## 2. Scope

### In scope

- W6 external integration surfaces
- outcome admission runtime API surface
- Feishu delivery bridge runtime path
- provider boundary freeze + runtime gate behavior
- repo-local autopilot machine control-plane
- clean-start operator procedure for local autopilot
- test and fixture expansion for the above

### Not claimed by this release

- W6 closeout complete
- `W6.S4a` complete
- `W6.RV1` complete
- remote deployment orchestration
- multi-environment rollout platform
- observability-suite expansion

## 3. Delivered changes

### 3.1 Outcome admission runtime surface

Delivered:

- `app/feedback/outcome_api.py`
- updated runtime and webhook-adjacent tests
- new `tests/test_outcome_admission_api.py`

Effect:

- repo now contains a concrete outcome admission API surface instead of leaving outcome flow only as a planning claim
- receipt/evidence path can be validated inside the repo test surface

### 3.2 First vendor delivery bridge: `adapter-feishu`

Delivered:

- `app/delivery/adapter_feishu.py`
- `app/delivery/bridge_result.py`
- `app/delivery/env_gate.py`
- `app/delivery/http_client.py`
- updates to `app/delivery/runtime.py`
- `.env.example`
- `tests/test_delivery_adapter_feishu.py`
- config updates in `configs/delivery.yaml`

Effect:

- `warning-agent -> adapter-feishu` bridge is now a real repo surface with env-gated activation and test coverage
- operator config seam is explicit instead of remaining implicit in local harness knowledge

### 3.3 Provider boundary freeze + runtime gate

Delivered:

- `app/investigator/provider_boundary.py`
- `app/investigator/local_primary.py`
- `app/investigator/cloud_fallback.py`
- `app/investigator/fallback.py`
- `configs/provider-boundary.yaml`
- `configs/escalation.yaml`
- `docs/warning-agent-provider-boundary.md`
- fixture updates:
  - `fixtures/evidence/checkout.cloud-investigation.json`
  - `fixtures/evidence/checkout.local-investigation.json`

Effect:

- provider truth is no longer only a design freeze; it is now reflected in runtime gate behavior
- smoke identity and future real-adapter activation seam remain explicitly separated
- fail-closed behavior is part of current truth

### 3.4 Repo-local machine control-plane for `pi-sdk`

Delivered:

- `docs/plan/README.md`
- `docs/plan/active_PLAN.md`
- `docs/plan/active_STATUS.md`
- `docs/plan/active_WORKSET.md`
- `docs/plan/warning-agent-autopilot-run-prompt.md`
- `tests/test_autopilot_control_plane.py`

Effect:

- `pi-sdk` local mode can now parse repo-local active control-plane truth for same-session continuation
- current machine path is serial and deterministic:
  - `W6.S4a`
  - `W6.RV1`

### 3.5 Local autopilot clean-start runbook

Delivered:

- `docs/warning-agent-local-autopilot-clean-start-runbook.md`
- `tests/test_autopilot_runbook.py`
- `README.md` link update

Effect:

- operator startup policy for local autopilot is now explicit:
  - new local run requires clean repo state
  - same-session continuation should use `/autopilot-resume`
  - preferred dirty-repo recovery path is checkpoint commit

### 3.6 Planning and execution pack updates

Updated:

- `docs/plan/warning-agent-production-integration-bridge-2026-04-20_PLAN.md`
- `docs/plan/warning-agent-production-integration-bridge-2026-04-20_STATUS.md`
- `docs/plan/warning-agent-production-integration-bridge-2026-04-20_WORKSET.md`
- supporting W6 design/closeout docs

Effect:

- richer human pack and machine pack now align on the current active W6 truth
- active slice remains `W6.S4a`; next queued slice remains `W6.RV1`

## 4. Current control-plane truth after this release

- machine control-plane anchor: `docs/plan/README.md`
- current active slice: `W6.S4a`
- intended next handoff: `execution-reality-audit`
- next queued slice: `W6.RV1`

Interpretation:

- this release enables automatic progression across the remaining W6 path
- this release does **not** claim that W6 has already been completed

## 5. Validation evidence

Latest repo-level evidence for the current state:

- `uv run pytest tests/test_autopilot_control_plane.py tests/test_autopilot_runbook.py` → `5 passed`
- `uv run pytest` → `156 passed`
- `uv run ruff check app tests scripts` → `pass`

Verification meaning:

- runtime/test surface is green at full-suite level for the committed repo state
- machine control-plane and clean-start runbook have direct regression coverage

## 6. Primary changed surfaces

| Area | Primary paths |
|---|---|
| Runtime delivery | `app/delivery/*`, `configs/delivery.yaml`, `.env.example` |
| Outcome admission | `app/feedback/outcome_api.py`, `tests/test_outcome_admission_api.py` |
| Provider runtime boundary | `app/investigator/*`, `configs/provider-boundary.yaml`, `configs/escalation.yaml` |
| Receiver/runtime operator surfaces | `app/receiver/alertmanager_webhook.py`, `app/delivery/runtime.py` |
| Control-plane | `docs/plan/README.md`, `docs/plan/active_*` |
| Operator runbook | `docs/warning-agent-local-autopilot-clean-start-runbook.md` |
| Validation | `tests/test_*` additions and updates |

## 7. Known residuals / caveats

1. W6 is still in progress; current active slice is `W6.S4a`.
2. `W6.RV1` reality audit still remains queued and is required before honest W6 closeout.
3. `pi-sdk` local mode still keeps the dirty-repo initial-run guard for a new session.
4. This repo state currently tracks generated `__pycache__` / `.pyc` artifacts as part of the committed working tree; that is a repo hygiene residual, not a product capability.

## 8. Recommended next step

Proceed serially:

1. execute `W6.S4a`
2. run slice validation and refresh richer + machine control-plane
3. enter `W6.RV1`
4. close out W6 or replan into W7 based on audit truth
