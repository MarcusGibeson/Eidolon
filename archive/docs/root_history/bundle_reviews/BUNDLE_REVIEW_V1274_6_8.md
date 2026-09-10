# Bundle Review v1274.6-v1274.8

## Scope

Environment freshness, fail-closed preflight, corrupt-state recovery, and Windows handoff reliability.

## Implemented

- Stale observations are detected and require refresh rather than being silently reused.
- Execution-sensitive environment preflight accepts only current observed facts.
- Assumed, inferred, unknown, and stale facts cannot satisfy sensitive requirements.
- Pure Windows drive-letter, UNC, extended-length, and long-path shape classification without inferring host OS.
- Malformed v1274 projection quarantine; missing facts are not reconstructed from assumptions.
- Native Windows review handoff for permissions, virtualenv/system Python, ports, provider/process state, resources, restart refresh, sharing violations, and long paths.

## Remaining native review

Actual Windows filesystem ACL/sharing behavior, long-path policy, process visibility, loopback port contention, resource APIs, provider-process presence, and restart-driven refresh remain Desktop Codex validation items.

## Focused evidence

`tools/v1274_6_8_environment_awareness_reliability_tests.py`
