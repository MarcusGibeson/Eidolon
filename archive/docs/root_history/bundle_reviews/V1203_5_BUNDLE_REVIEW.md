# v1203.3-v1203.5 Bundle Review

This bundle adds project-owned Python test discovery and bounded execution to the supervised Python CLI campaign.

## Implemented

- Allowlisted `tests/test_*.py` and `tests/*_test.py` discovery.
- Maximum 12 tests, 256 KiB per test, 1 MiB aggregate, and 12-second timeout per test.
- Isolated Python execution with no stdin, no bytecode, no user site, minimal environment, and private external HOME.
- AST-based rejection of network and process-capability imports.
- Digest-only path and output evidence.
- Idempotent restart recovery and duplicate-operation convergence.
- Seven-stage checkpoint ending in project-owned tests.

## Authority boundaries

No dependency installation, network access, selected-project apply, repair, source mutation, model management, release promotion, certification, or independent authority is granted.
