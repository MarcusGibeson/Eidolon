# v1208.9 Python Test Adapter Checkpoint Review

v1208.0-v1208.9 adds a general, bounded Python project test adapter without replacing the earlier Python CLI-specific checkpoints.

## Bound stages

1. Exact proposal revision
2. Exactly-once approval
3. Grounded Python planning
4. Validated structured generation
5. Verified isolated workspace
6. Sealed Python operation journal
7. Bounded Python test result
8. Privacy and operator-review authority boundary

## Supported execution

- Standard-library `unittest` is the default.
- `pytest` is used only when project tests/configuration request it and the selected interpreter already provides it.
- No dependency installation or package-manager command is permitted.
- Syntax, test count, input size, output size, timeout, interpreter discovery, and process cleanup are bounded.
- Network, subprocess, native-extension, debugger, and unsafe external write capabilities are rejected or blocked.

Passing and failing results are both checkpointable evidence. Neither grants repair, apply, rollback, release, model-management, or independent authority.
