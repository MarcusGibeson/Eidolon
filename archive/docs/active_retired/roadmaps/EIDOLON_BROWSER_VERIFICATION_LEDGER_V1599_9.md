# Eidolon Browser Verification Ledger: v1599.9

Candidate status: **unpromoted source-only Mobile Browser campaign candidate**.

All suites below were run against the cumulative v1501.3-to-v1599.9 working tree with runtime state redirected outside source where applicable. No suite result is a native Windows, configured-provider, installation, promotion, or operator-trial certification claim.

## Current supervised-development lineage

| Suite | Reported pass count | Result |
|---|---:|---|
| `tools/v1501_0_supervised_initiative_queue_tests.py` | 43 | PASS |
| `tools/v1501_0_1_source_only_workspace_boundary_repair_tests.py` | 12 | PASS |
| `tools/v1501_1_candidate_review_installation_tests.py` | 23 | PASS |
| `tools/v1501_2_sustained_supervised_initiative_tests.py` | 22 | PASS |
| `tools/v1501_3_initiative_evidence_intake_tests.py` | 27 | PASS |
| `tools/v1508_9_initiative_evidence_review_checkpoint_tests.py` | 48 | PASS |
| `tools/v1516_9_initiative_value_model_checkpoint_tests.py` | 36 | PASS |
| `tools/v1525_9_value_prioritized_selection_checkpoint_tests.py` | 37 | PASS |
| `tools/v1550_9_defect_feedback_intelligence_checkpoint_tests.py` | 21 tests / 37 assertions | PASS |
| `tools/v1575_9_repair_retry_intelligence_checkpoint_tests.py` | 13 tests / 35 assertions | PASS |
| `tools/v1599_9_multi_cycle_supervised_campaign_checkpoint_tests.py` | 15 tests / 38 assertions | PASS |

Reported current-lineage total: **297 checks/test cases**, with assertion counts additionally reported by the newer checkpoint suites where available.

## Affected retained verification

| Suite | Reported pass count | Result |
|---|---:|---|
| `tools/v1490_0_2_dynamic_improvement_discovery_tests.py` | 69 | PASS |
| `tools/v1500_9_1_release_self_knowledge_tests.py` | 32 | PASS |
| `tools/v1250_3_release_metadata_consolidation_tests.py` | 94 | PASS after repairing the stale generated release-metadata manifest |
| `tools/v1250_4_checkpoint_registry_consolidation_tests.py` | 118 | PASS |
| `tools/v1250_5_compatibility_registry_migration_tests.py` | 100 | PASS |

Selected focused plus retained total: **710 reported checks/test cases**.

The dynamic-discovery retained suite includes same-length source/test replacement with restored-mtime cache invalidation and completed with 69/69 checks. Its real-source timing in this environment was approximately 17.8 seconds cold and 123 ms warm; this is Browser-container evidence only, not native Windows performance certification.

## Repair discovered during release verification

After advancing active release truth to v1599.9, the retained v1250.3 consolidation suite correctly rejected the stale `docs/release/release_metadata_manifest.json`, which still named v1501.3. The manifest was regenerated for v1599.9 with the current generated-facade hashes and the suite then passed 94/94. This is retained metadata coherence, not release promotion.

## Final packaging verification still required

The final handoff process must remove caches/bytecode, compile Python source without writing into the source tree, verify source-only privacy, package exactly one `Eidolon/` root, fresh-extract the exact ZIP, rerun the critical cumulative checkpoint suites, and compare extracted bytes to the packaged manifest. Those results are reported in the external final handoff so this file does not recursively change the ZIP after it is verified.
