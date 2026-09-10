# Eidolon v1340.9 Tool-Execution Checkpoint Validation

## Scope

v1340 closes Phase 4, Tool Use and Isolated Execution. The checkpoint integrates the v1331-v1339 contracts into one bounded, candidate-only execution campaign without expanding operator authority.

The ordinary execution path can create a disposable candidate workspace, perform an owned structured file change, stage and commit only receipt-owned Git changes, run a bounded verification process, validate browser-visible behavior with real Chromium evidence where the host permits it, start and stop a bounded loopback service, reconcile tool results, and clean up owned runtime/workspace state. No checkpoint behavior applies changes to the selected source, installs/promotes/releases a candidate, expands workspace scope, or grants authority from evidence alone.

## Focused verification

The final focused suites pass on the v1340.9 source:

- `v1340_0_2_multi_tool_execution_foundations_tests.py`: 5/5
- `v1340_3_5_multi_tool_execution_integration_tests.py`: 7/7
- `v1340_6_8_multi_tool_execution_reliability_tests.py`: 7/7
- `v1340_9_multi_tool_execution_checkpoint_tests.py`: 5/5
- retained release-metadata consolidation: 94/94
- retained checkpoint-registry consolidation: 118/118

The integration fixture uses a real disposable Git worktree, a real owned file patch and commit, a real bounded child verification process, real Chromium, a real loopback service, tool-result reconciliation, and deterministic cleanup. The selected Eidolon source remains unchanged by the campaign.

## Ten-arc Desktop Codex / Windows architecture review

The scheduled v1340 review completed with no blocking architecture finding:

- Phase 4 has no internal import cycle across the v1331-v1340 implementation modules.
- Dependency direction remains layered rather than forming a second competing tool-runtime stack.
- The largest Phase 4 module observed during review is `workspace_isolation.py` at 522 lines; no blind line-count split was justified.
- retained natural-conversation/command distinction: 138/138
- v1320 real-tree project-understanding checkpoint: 4/4
- v1253.9.1 pre-Codex runtime-coherence repair: 81/81
- v1253.9.2 Windows-runtime-coherence repair: 19/19

This Linux/container review is source-level evidence. Native Windows execution remains external evidence and is not claimed by this checkpoint.

The managed Chromium installation on this host applies a URL block policy that prevents loopback navigation. v1337 therefore records `browser_policy` as the limitation and uses a real Chromium offline-document path only for DOM/render/screenshot evidence. The checkpoint does not misrepresent that fallback as loopback/server validation.

## Broad segmented verification and repair history

The first full v1340 segmented-verifier attempt passed stages 1-8 and then failed the final dashboard-interface suite, `v1253_6_8_performance_governance_tests.py`. A direct rerun passed, but an exact-resume verifier attempt reproduced the same failure in the clean external snapshot. Both failed receipts were retained as diagnostic evidence rather than discarded.

Diagnosis showed a verifier-duration coherence defect rather than a v1340 product regression. `runtime_efficiency_benchmark._subprocess_seconds` used a hard 15-second child-process timeout even though the retained benchmark intentionally measures hardware-sensitive cold-start behavior. Clean-snapshot cold starts on this host approached that timeout, allowing scheduling/storage variance to terminate the measurement before the historical performance budget could evaluate it.

The narrow repair changes only the measurement subprocess allowance from 15 seconds to 30 seconds. Historical performance thresholds, acceptance budgets, and retained tests were not weakened or rewritten. The repaired source then passed:

- v1253.6-v1253.8 performance governance: 25/25
- v1253.9.1 runtime coherence: 81/81
- v1253.9.2 Windows-oriented runtime coherence: 19/19

Because shared verification infrastructure changed, the complete segmented verifier was restarted from stage 1 on a fresh external snapshot rather than reusing earlier passed stages.

Final broad result:

- segmented stages: 10/10 passed
- failed stages: 0
- dashboard-interface: 7/7 suites passed, including the previously failing retained performance-governance suite
- retained-checkpoints: 16/16 suites passed
- source unchanged throughout verification: true
- total final verifier elapsed time: approximately 541.3 seconds

The persisted final receipt is `v1340_segmented_final_receipt.json` outside the source tree. Earlier failed diagnostic receipts also remain outside the source package.

## Authority, privacy, and recovery boundaries

Tool availability, preconditions, isolation evidence, successful process results, browser evidence, service readiness, reconciliation judgments, commits, or checkpoint success do not create authority. The active operator-selected grant remains the authority source. Candidate execution remains workspace-bound and low-level operations continue to fail closed on stale/tampered lineage, missing preconditions, ambiguous ownership, uncertain side effects, or boundary conflicts.

External publication, destructive system operations, secrets, model installation/deletion, account changes, financial actions, installation, promotion, release, permanent standing authority, and unrestricted autonomy remain outside this checkpoint unless separately and explicitly governed.

The release remains source-only. Runtime/private records, logs, verifier receipts, screenshots, candidate worktrees, process/service state, and other execution evidence are not packaged as source authority.

## Checkpoint decision

v1340.9 satisfies the Phase 4 Tool-Execution Checkpoint gate. The exact next roadmap arc is **v1341 - Python Implementation**.
