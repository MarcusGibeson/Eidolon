# Eidolon v1263.0-v1263.9 Priority Selection Arc Review

## Scope

v1263 consumes a validated v1262 development backlog and creates a separate, sealed, read-only priority decision. It does not mutate the backlog and does not create development, scheduling, execution, application, installation, release, or self-update authority.

## v1263.0-v1263.2 Priority Selection Foundations

Implemented `priority_selection_foundations.py` with:

- deterministic evaluation of user value, reliability impact, urgency, reversibility, effort cost, uncertainty cost, risk cost, and dependency readiness;
- explicit factor weights and points;
- provenance for inferred versus explicitly supplied bounded priority context;
- dependency-blocked item ineligibility;
- shared ranking for equal scores;
- exact tie, empty backlog, and all-blocked no-defensible-selection states;
- near-tie margin and confidence reporting;
- immutable v1262 backlog lineage;
- semantic validation of factor bands, arithmetic, ranks, dependencies, item digests, and selected-item semantics;
- content-minimized public projection;
- no action authority.

## v1263.3-v1263.5 Priority Integration

Implemented `priority_selection.py` as a direct v1261 -> v1262 -> v1263 read-only flow.

- The backlog is generated and sealed before selection.
- Optional bounded priority context may supply user value, urgency, and reversibility by exact objective code and evidence digest.
- Context does not carry raw operator text or project content.
- The selected item includes content-minimized comparative rationale against alternatives.
- Contradictory evidence preserves the v1262 evidence-resolution dependency; the dependent repair remains blocked and cannot be selected first.
- Changed evidence changes backlog and selection lineage.
- No proposal or schedule is created.

## v1263.6-v1263.8 Reliability

Implemented `priority_selection_reliability.py` with:

- source/backlog freshness validation;
- restart-deterministic regeneration;
- concurrent duplicate convergence;
- dependency-blocked selection rejection;
- exact and near-tie handling;
- dependency-cycle fail-closed behavior inherited from v1262 validation;
- tamper rejection even when an attacker recomputes the outer selection digest after changing score arithmetic;
- long-path fixtures;
- read-only health inspection and Desktop Codex handoff.

## v1263.9 Checkpoint

Implemented a read-only registry-backed checkpoint that confirms the v1261 evidence layer, v1262 backlog layer, and v1263 priority layer remain distinct. Alternative planning is explicitly deferred to v1264.

## Practical Eidolon self-selection

A read-only v1263 pass over Eidolon's own source produced the same two candidate work classes previously surfaced by v1262: current test-outcome evidence acquisition and maintenance/limitation-signal triage. Under conservative inferred factors, current test-outcome evidence acquisition outranks maintenance-signal triage. No proposal, schedule, execution, or self-modification is created from that result.

## Authority boundary

Priority selection is judgment only. The selected item is not a development proposal, approval, execution plan, application authorization, release authorization, or self-update authorization. v1254 and v1255 remain the execution/application authority layers, and v1264 remains a separate planning stage.
