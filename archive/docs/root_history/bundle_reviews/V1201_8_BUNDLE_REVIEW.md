# v1201.6-v1201.8 Bounded Browser and JavaScript Validation Review

## Implemented

- Added revision-, workspace-, preview-, planning-, generation-, and approval-bound validation records in external runtime data.
- Added a bounded browser-document adapter for HTML entrypoint, title, viewport, duplicate IDs, local assets, rejected paths, and missing assets.
- Added a bounded JavaScript syntax adapter using only `node --check`, with file-count, per-file, aggregate-size, timeout, minimal-environment, and no-stdin limits.
- Added idempotent resume and tamper detection. Existing valid results do not execute commands again.
- Added digest-only public evidence and a POST-only dashboard action.
- Preserved selected-project and Eidolon-source immutability. No generated change is applied and no repair is attempted.

## Authority boundaries

Validation may execute only the allowlisted Node syntax command against the isolated external workspace. It does not run application JavaScript, access the network, install packages, contact a provider, mutate a selected project, apply generated output, modify Eidolon source, manage models, promote a release, or infer further approval.

## Deferred

- Real browser automation and rendered DOM behavior.
- JavaScript unit-test discovery and execution.
- Node package test adapters.
- Python command-line implementation and test adapters.
- Evidence-grounded diagnosis and bounded repair.
