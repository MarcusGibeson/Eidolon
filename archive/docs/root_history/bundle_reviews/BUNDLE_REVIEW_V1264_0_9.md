# Eidolon v1264.0-v1264.9 Alternative Planning and Simulation Arc Review

## Scope

v1264 consumes one validated v1263 priority decision and creates a separate, sealed, read-only alternative-planning artifact. It generates multiple bounded implementation strategies for the exact selected v1262 work item, predicts strategy-specific failure modes, compares tradeoffs, and selects at most one defensible plan. It does not mutate the v1262 backlog or v1263 priority decision and does not create proposal, provider, execution, application, installation, release, or self-modification authority.

Authoritative input: `Eidolon_v1263_9_priority_selection_checkpoint_source_only.zip`.
Verified baseline SHA-256: `059ED2BD92784212EFFFAB3443D2908B98EC54B778650C3F2E5A2E47F791FBD8`.

## v1264.0-v1264.2 Alternative Planning Foundations

Implemented `conscious_agent/alternative_planning_foundations.py` with:

- exact v1262 backlog and v1263 selection lineage;
- unique-priority precondition and explicit no-plan result when no unique priority exists;
- 2-4 bounded competing approaches;
- strategy-specific implementation-step and verification-step codes;
- predicted failure modes carrying likelihood, impact, mitigation, falsification condition, digest, and explicit `predicted` epistemic status;
- success-confidence, effort, risk, uncertainty, and reversibility tradeoffs;
- deterministic simulation scoring;
- exact strategy-tie handling with no lexical winner;
- assumptions, completion conditions, blockers, and operator-review requirement;
- semantic validation that independently recomputes scores and rejects resealed score/failure-semantics tampering;
- content-minimized public projection;
- explicit denial of all execution/application/self-modification authority.

Focused suite: `tools/v1264_0_2_alternative_planning_foundations_tests.py`.

## v1264.3-v1264.5 Alternative Planning Integration

Implemented `conscious_agent/alternative_planning.py` as a direct v1261 → v1262 → v1263 → v1264 read-only flow.

Strategy families are distinct by work class:

- evidence acquisition: focused existing verification, layered focused→regression verification, fresh-extract validation;
- evidence resolution: same-condition reproduction, independent secondary check, bounded defer-until-stronger-evidence;
- reliability/test work: diagnose→minimal repair, guarded structural repair, additional evidence before repair;
- maintenance/limitation work: targeted investigation, component-cluster review, historical evidence crosscheck.

Optional plan context may adjust only bounded strategy factors and is bound by evidence digest. Changed assessment/backlog/priority evidence produces changed plan lineage. The selected plan includes content-minimized comparative rationale.

Focused suite: `tools/v1264_3_5_alternative_planning_integration_tests.py`.

## v1264.6-v1264.8 Reliability

Implemented `conscious_agent/alternative_planning_reliability.py` with:

- source, backlog, priority, and plan freshness checking;
- stale-source and stale-priority rejection;
- restart-deterministic plan regeneration;
- eight-way concurrent duplicate convergence;
- exact strategy-tie fail-closed behavior;
- resealed score tamper rejection;
- failure-prediction epistemic tamper rejection;
- bounded-context validation;
- long-path coverage;
- read-only health inspection;
- bounded Desktop Codex handoff.

Focused suite: `tools/v1264_6_8_alternative_planning_reliability_tests.py`.

## v1264.9 Checkpoint

Implemented `conscious_agent/alternative_planning_checkpoint.py` and registered v1264.0-v1264.9 in the canonical release/checkpoint authorities.

The checkpoint is read-only and content-free. It does not contact providers, run commands/tests, read private runtime state, create proposals/schedules, modify source/projects, or begin self-modification.

Focused suite: `tools/v1264_9_alternative_planning_checkpoint_tests.py`.

## Practical Eidolon self-planning observation

A read-only v1261→v1264 pass over Eidolon's own source produces two v1262 backlog candidates. v1263 selects `acquire_current_test_outcome_evidence`. v1264 generates three distinct strategies:

1. `focused_existing_verification` — simulation score 13;
2. `layered_focused_then_regression` — simulation score 11;
3. `fresh_extract_validation_campaign` — simulation score 4.

The selected strategy is `focused_existing_verification`, with a two-point margin and **low** selection confidence. The low confidence is intentional: the top two plans are close enough that operator review remains meaningful. Predicted failures include incomplete verification surface, environment blockers, regression-budget exhaustion, clean-environment mismatch, and validation-budget exhaustion.

No development proposal, provider call, execution, application, or source mutation occurs from this result.

## Authority boundary

v1264 is judgment only. It does not execute the selected strategy, create an implementation proposal, modify an isolated Eidolon copy, apply changes, install dependencies, contact providers, update the active installation, or grant permanent approval. **v1265 Isolated Self-Modification** is the next separate arc.
