# v1263.0-v1263.9 Focused Validation

## Current arc

- `tools/v1263_0_2_priority_selection_foundations_tests.py`
- `tools/v1263_3_5_priority_selection_integration_tests.py`
- `tools/v1263_6_8_priority_selection_reliability_tests.py`
- `tools/v1263_9_priority_selection_checkpoint_tests.py`

## Retained dependency evidence

- v1262 foundations, integration, reliability, and checkpoint.
- v1261 evidence-based inspection foundations, integration, reliability, and checkpoint.
- v1260 Coding Alpha checkpoint.
- v1259-v1254 retained read-only checkpoints.
- v1250.3 release metadata and v1250.4 checkpoint registry.
- v1247.9 privacy/security checkpoint.

## Required release checks

1. Run all four v1263 suites provider-free and with runtime data redirected outside the source tree.
2. Run the retained v1262 and v1261 suites because v1263 depends directly on both contracts.
3. Run retained checkpoints through v1254.9.
4. Validate release metadata and checkpoint registry.
5. Parse every source Python file with bytecode disabled.
6. Run source privacy/secret verification.
7. Build from the source-only package inventory only.
8. Verify final ZIP privacy separately from root privacy.
9. Fresh-extract beneath exactly one `Eidolon/` root.
10. Compare every packaged file byte-for-byte.
11. Rerun v1263, metadata/registry, privacy, and Python parsing from the fresh extraction.

## Native Desktop Codex focus

- real Windows case-insensitive path semantics and NTFS junction/reparse containment;
- concurrent duplicate priority requests across processes/tabs;
- restart after backlog generation but before selection materialization;
- stale source/evidence changes between backlog and priority review;
- exact ties and low-margin near-ties;
- prerequisite selection when downstream work is dependency-blocked;
- confirmation that selection cannot create a proposal, schedule, execution, application, installation, or self-update.
