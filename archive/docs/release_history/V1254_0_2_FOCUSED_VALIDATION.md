# v1254.0-v1254.2 Focused Validation

Validation target: Isolated Coding Execution Bundle A foundations.

## Required focused evidence

- `tools/v1254_0_2_isolated_coding_execution_foundations_tests.py`: 125/125 passed.
- Python source compilation without bytecode output: 2,605 files compiled successfully.
- Root source-only privacy scan: 0 forbidden runtime entries and 0 private-content findings.
- Final source-only archive privacy scan: 0 forbidden runtime entries and 0 private-content findings.
- Fresh extraction reproduced exactly one `Eidolon/` root with file-hash parity and reran the v1254 suite at 125/125.
- Source immutability is asserted inside the v1254 focused suite while request, inspection, planning, workspace creation, restart restoration, cancellation, and stale-source behavior execute against temporary fixtures.

## Retained compatibility checkpoints

- `tools/v1250_3_release_metadata_consolidation_tests.py`: 94/94 passed.
- `tools/v1250_4_checkpoint_registry_consolidation_tests.py`: 118/118 passed.
- `tools/v1201_9_small_website_implementation_checkpoint_tests.py`: 89/89 passed.
- `tools/v1238_9_broader_project_language_adapters_checkpoint_tests.py`: 27/27 passed.
- `tools/v1247_9_privacy_security_secret_management_audit_checkpoint_tests.py`: 59/59 passed.
- `tools/v1180_9_supervised_project_inspection_planning_checkpoint_tests.py`: 81/84. Its three misses are frozen documentation-era assertions that require v1180/v1181 to remain the current roadmap/README source; the functional inspection/planning assertions in that retained checkpoint pass. Current release metadata and the newer retained checkpoint suites above pass.

## Bundle A containment evidence

The focused suite verifies that the selected fixture project is byte-for-byte unchanged before and after isolated workspace preparation. It rejects `..` traversal, excludes private/runtime data, refuses symlink escape scanning, simulates the Windows reparse-point flag used by junctions, blocks stale-source planning, restores durable requests after module reload, cleans cancelled workspaces, and verifies all dangerous authority flags remain denied.

No provider contact, product command execution, product test execution, source application, installation, release, or independent authority is exercised or granted by this validation.
