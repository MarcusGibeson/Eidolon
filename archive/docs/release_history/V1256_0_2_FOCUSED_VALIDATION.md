# v1256.0-v1256.2 Focused Validation

## Scope

Persistent Development Sessions Bundle A establishes a durable, restart-safe development-session projection over the existing v1254 Isolated Coding Execution and v1255 Controlled Application and Rollback records. It does not create a parallel execution product or new mutation authority.

## Implemented contracts

- One deterministic persistent session ID per sealed coding request.
- Session state rebuilt from current sealed request, inspection, plan, workspace, isolated-execution/review, controlled-application, application-result, and rollback-result records.
- Digest-linked requirements, acceptance criteria, constraints, prohibited actions, expected artifacts, verification plan, and plan lineage.
- Content-minimized attempt and verification evidence. Raw provider responses and raw test output are not copied into the persistent session.
- Restart-safe restoration and cancellation continuity.
- Explicitly denied automatic resume, duplicate execution, provider contact, command/test execution, dependency installation, project mutation, source application, rollback, installation, promotion, certification, release, permanent approval, and independent authority.

## Deterministic evidence

`tools/v1256_0_2_persistent_development_session_foundations_tests.py`: **49/49 passed**.

The suite is provider-free and verifies deterministic identity/idempotency, digest-linked lineage, authority denial, content-minimized attempt/test evidence, fresh-process restoration, cancellation durability, source immutability, and fail-closed handling of a tampered session record.
