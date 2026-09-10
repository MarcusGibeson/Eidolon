# Desktop Codex Handoff v1271.9

Validate the source-only v1271.9 candidate on native Windows without installing over an operator-active Eidolon environment.

Focus on: (1) process lifetime and clean/forced shutdown during an active long-running session; (2) atomic external-runtime JSON replacement and filesystem lock behavior; (3) expired heartbeat/lease recovery and owner-generation transitions; (4) long NTFS paths and, where available, junction/reparse interactions; (5) restart between v1270 candidate preparation, candidate execution, verification/repair, and operator review; (6) confirmation that resume/reconciliation does not duplicate provider, tool, or selected-test activity; and (7) harness-budget reporting when long verification should be split instead of granted a blanket timeout increase.

Do not treat the advisory v1271 lease as v1273 exactly-once concurrency. Do not grant any provider/test/update/application/rollback/release authority during review. v1272 has not been started.
