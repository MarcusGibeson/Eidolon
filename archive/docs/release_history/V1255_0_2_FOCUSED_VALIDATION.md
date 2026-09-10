# v1255.0-v1255.2 Focused Validation

Bundle A establishes the Controlled Application and Rollback preparation boundary on top of the sealed v1254 isolated-coding lineage.

## Implemented

- Immutable application packet bound to the request, inspection, isolated execution result, review, workspace manifest, candidate manifest, and exact per-path baseline/candidate digests.
- Selective conflict detection limited to candidate-changed paths. Unrelated operator edits may remain present without invalidating the packet.
- Windows case-insensitive alias detection for affected paths.
- Deferred private backup capture. Backup contents are not collected while merely preparing/reviewing an application.
- Separate rollback preparation contract. Preparation never grants application or rollback execution authority.
- Content-minimized public records that omit the selected-project path and private backup bytes.

## Deterministic focused evidence

`tools/v1255_0_2_controlled_application_foundations_tests.py`: **44/44 passed**.

Coverage includes exact lineage, candidate operation classification, selective conflicts, unrelated edits, stale same-path edits, private backup deferral/integrity, request cancellation, content minimization, source immutability, and denied authority.

No provider contact, selected-project mutation, dependency installation, release action, permanent approval, or independent authority is granted by Bundle A.
