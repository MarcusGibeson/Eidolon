# v1202.3-v1202.5 Project-Owned JavaScript Test Execution

This bounded bundle adds a seventh, revision-bound stage to the supervised JavaScript-tool flow. After the existing six-stage v1202.2 checkpoint succeeds, Eidolon discovers only allowlisted `tests/**/*.test.js`, `.test.mjs`, or `.test.cjs` files in the exact isolated workspace and executes each with Node's built-in test runner.

## Safety and authority

- No dependency installation or package-manager execution.
- No network-capable Node modules in project-owned test files.
- Maximum 12 test files, 256 KiB each, 1 MiB aggregate.
- Twelve-second timeout per test file, no stdin, minimal environment, captured output.
- Public evidence contains only counts, exit classes, and digests.
- Test failure grants no repair, apply, source, model, release, or independent authority.
- Selected projects and Eidolon source remain unchanged.

## Lifecycle

The final checkpoint binds proposal, approval, planning, generation, workspace, validation, and project-test receipts. Duplicate calls resume the same record and do not contact the provider or execute tests again.

## Deferred

Result review and explicit operator disposition remain deferred to v1202.6-v1202.8. Applying changes to a selected project remains out of scope.
