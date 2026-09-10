# v1266.0-v1266.9 Focused Validation

## Required behavioral suites

- `tools/v1266_0_2_intelligent_test_selection_foundations_tests.py`
- `tools/v1266_3_5_intelligent_test_selection_integration_tests.py`
- `tools/v1266_6_8_intelligent_test_selection_reliability_tests.py`
- `tools/v1266_9_intelligent_test_selection_checkpoint_tests.py`

## Retained boundaries

At minimum retain the v1265 isolated self-modification behavioral/checkpoint suites, v1264-v1254 checkpoint lineage, v1250 release metadata/checkpoint registry consolidation, v1247 privacy/security audit, source-only package privacy, and whole-tree Python parsing.

## Assertions

Validation must establish that:

1. the v1265 candidate and result lineage are exact and fresh;
2. changed paths and affected surfaces deterministically drive selection;
3. direct-import tests are focused and transitive/high-risk surfaces expand regression coverage;
4. trusted tests come from the active baseline, not provider-created candidate content;
5. modified/deleted trusted tests block selection and new candidate tests remain supplemental/untrusted;
6. stale candidate workspaces and semantically tampered selection records fail closed;
7. duplicate and concurrent selection converges deterministically;
8. no selected test is executed by v1266;
9. no provider is contacted by v1266;
10. active source and candidate workspace remain unmodified by selection;
11. application/self-update authority remains false;
12. final source-only archive contains no runtime/private data and reproduces the same v1266 evidence after fresh extraction.
