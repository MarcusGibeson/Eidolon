# v1254.3-v1254.5 Bundle B Review

## Scope

Bundle B integrates the v1254.0-v1254.2 request, inspection, plan, and disposable-workspace foundation into Eidolon's existing supervised development campaign and ordinary conversation path. It intentionally stops before selected-project application.

## Implemented

- Added `isolated_coding_execution.py` with one exact, digest-bound execution authorization tied to the sealed request, inspection, plan, source manifest, and disposable workspace.
- Provider generation is permitted only after that exact authorization. Generated changes are schema-bound, path-contained, source-relevant, size-bounded, syntax-checked, and written only to the disposable workspace.
- Added bounded Python, Node/JavaScript, and static verification using the existing adapter primitives rather than an unrestricted shell surface.
- Added one initial implementation plus at most two repair attempts. Failed verification is summarized by content-minimized evidence before a repair attempt.
- Added sealed attempt records, verification evidence, review records, and an operator-reviewable diff. Public projections exclude raw provider output, raw test output, private paths, and private content.
- Bridged approved selected-project ordinary-chat development proposals into the v1254 isolated execution chain. Proposal approval still does not authorize implementation: a second exact isolated-execution authorization is required.
- Successful isolated execution explicitly reports that the selected project was not modified and that application requires a later authority stage.

## Evidence

`tools/v1254_3_5_isolated_coding_execution_integration_tests.py`: **54/54 passed**.

The deterministic fixture starts with an incorrect implementation, records a failing test result, performs one bounded repair, passes verification, produces a reviewable diff, and leaves the selected project and its excluded `.env` unchanged. Replay returns the sealed result without recontacting the provider. Stale selected source blocks provider contact.

## Authority boundary

Bundle B does not authorize selected-project mutation, source application, installation, release, permanent approval, dependency installation, unrestricted shell execution, or independent self-update.
