# Eidolon Mobile Browser Era 1 Work Ledger: v1501.4-v1599.9

Status: **cumulative unpromoted source-only Mobile Browser candidate**.

Authoritative input: v1501.3 Initiative Evidence Intake. This ledger records portable work only. It does not claim installation, promotion, release certification, native Windows execution, provider contact, private-runtime inspection, or operator-trial acceptance.

Exact resume point: **v1600 - operator-invoked Desktop Era 1 gate**.

## Completed portable roadmap ranges

### v1501.4-v1508.9: Evidence review and hardening

- Added a digest-bound operator review overlay over the existing v1501.3 normalized evidence intake rather than creating a second evidence owner.
- Added confirm, defer, cancel, and correction controls with stale-digest rejection, restart persistence, exactly-once replay, content-free public receipts, and compound-command refusal.
- Added explicit evidence contract/status projection for production integration.
- Focused checkpoint: `tools/v1508_9_initiative_evidence_review_checkpoint_tests.py`.

### v1509-v1516.9: Capability-value model

- Added scoring for user impact, frequency, severity, confidence, reversibility, effort, dependency risk, strategic value, and evidence quality.
- Added explicit resistance to duplicate lineages, structural-only busywork, easy-but-low-value work, stale evidence, and test-count metric gaming.
- Preserved important unmapped findings as visible blockers rather than pretending they are executable candidates.
- Focused checkpoint: `tools/v1516_9_initiative_value_model_checkpoint_tests.py`.

### v1517-v1525.9: Value-aware production selection

- Integrated value prioritization into the existing supervised initiative production path.
- Preserved the existing queue as the authoritative lifecycle owner and kept discovery evidence identity separate from value-evidence identity.
- Added high-value-unmapped blocking behavior and operator defer release without granting proposal/install authority.
- Repaired duplicate candidate evidence mapping to preserve the highest impact score rather than whichever duplicate row happened to be processed last.
- Focused checkpoint: `tools/v1525_9_value_prioritized_selection_checkpoint_tests.py`.

### v1526-v1533.9: Finding records

- Reused the existing private v1089 conversation-evaluation finding owner instead of creating a duplicate defect database.
- Added content-free development projections over private findings with attributable IDs/digests and bounded public fields.
- Explicitly deferred any private runtime-schema expansion needed for richer expected/actual/reproduction/frequency fields.

### v1534-v1541.9: Reproduction pipeline

- Added deterministic synthetic reproduction scenarios and privacy-safe fixture generation for suitable finding classes.
- Kept private conversation content out of release evidence and test fixtures.

### v1542-v1550.9: Live feedback intelligence

- Normalized dashboard feedback, action failures, provider failures, and operator-trial scores into attributable development evidence classes.
- Added deduplication, retraction, stale-evidence, and privacy behavior without contacting providers.
- Integrated the existing private finding aggregation into the current initiative-evidence intake path.
- Focused checkpoint: `tools/v1550_9_defect_feedback_intelligence_checkpoint_tests.py`.

### v1551-v1558.9: Failure taxonomy

- Added syntax, import, test, timeout, stale-baseline, scope, dependency, provider, acceptance-criterion, security/authority, and unknown failure classes.
- Added content-free failure receipts that do not echo private/provider failure text.

### v1559-v1566.9: Bounded repair and retry

- Added a maximum two-cycle repair budget inside the original proposal, workspace, allowlist, and evidence lineage.
- Prevented scope expansion and stopped hard on security/authority or scope violations.
- Repaired a real continuation defect discovered during this campaign: after a clean failed isolated implementation restored its disposable workspace, the continuation path could remain blocked instead of re-arming the same proposal. The same authorized proposal can now re-enter the prepared state under bounded repair accounting.

### v1567-v1575.9: Recovery checkpoint foundations

- Added portable interruption/restart/duplicate/provider-loss/stale-source/partial-file/exhausted-budget contracts and tests.
- Preserved active-source and installation-authority boundaries.
- Focused checkpoint: `tools/v1575_9_repair_retry_intelligence_checkpoint_tests.py`.

### v1576-v1583.9: Multi-cycle campaign planning

- Added restart-safe three-to-five initiative campaign plans with dependency graphs, success criteria, stop conditions, priority scores, resource estimates, and revision rules.
- Added dependency-cycle rejection and current-evidence revalidation before activation.
- Kept campaign membership from becoming proposal, provider, installation, promotion, model-management, or source-mutation authority.

### v1584-v1591.9: Pacing and interruption

- Added maximum cycle/failure budgets, one-active-item ownership, metadata-lock coordination, pause/resume/cancel, and explicit quiet/wake controls.
- Quiet mode now actually blocks new campaign selection until an exact digest-bound wake control succeeds.
- Controls are restart-safe, stale-digest resistant, idempotent, and reject compound authority requests.

### v1592-v1599.9: Portable Era 1 checkpoint preparation

- Integrated campaign reconciliation with the real continuation path so installed proposal receipts can reconcile terminal campaign items exactly once and the next still-current dependency-ready item can be selected.
- Added stale-evidence skipping, priority activation, campaign item lifecycle receipts, and checkpoint declarations for native evidence still required at v1600.
- Updated release/version truth to identify this source as an **unpromoted v1599.9 Mobile Browser candidate**, not an installed/certified release.
- Focused checkpoint: `tools/v1599_9_multi_cycle_supervised_campaign_checkpoint_tests.py`.

## Defects repaired during this campaign

1. **Duplicate candidate impact overwrite**: duplicate candidate evidence could retain a lower later score. The queue now keeps the highest impact score.
2. **Failed-workspace retry dead end**: a clean restored isolated workspace could remain blocked after a safe implementation failure. The continuation path now re-arms the same proposal within the bounded repair budget and original scope.
3. **Quiet-period no-op**: campaign state exposed a quiet flag without enforcing it. Exact quiet/wake controls now mutate the digest-bound campaign state, and quiet mode blocks new initiative selection.
4. **Runtime debris during browser tests**: a test-generated `data/settings.json` was detected by baseline comparison and removed. Runtime data is not part of the source-only candidate.

## Verification summary

Focused and retained verification is recorded in the final session handoff and changed-file manifest. The campaign-specific suites cover evidence review, value modeling, value-aware selection, defect/feedback intelligence, bounded repair/retry, and multi-cycle campaign behavior. Retained v1501.0-v1501.3 lifecycle suites remain part of the affected regression set.

## Authority result

No browser change grants installation, promotion, certification, provider contact, model management, secret access, destructive-operation, live-source mutation, or authority expansion. Preview/read-only and isolated-development boundaries remain distinct. Generated prose is never treated as execution evidence.
