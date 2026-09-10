# v1256.6-v1256.8 Focused Validation

## Scope

Bundle C hardens session restoration, recovery, metadata integrity, concurrency, long paths, and operator handoff while retaining the v1254/v1255 authority boundaries.

## Reliability behavior

- Stale selected-project source becomes a blocker before an execution authorization is resurfaced.
- Expired isolated-execution/application leases are projected as recovery states that require the original exact authorization; no provider work is replayed automatically.
- Invalid session/index/event metadata is quarantined and reconstructed from authoritative sealed development lineage when possible.
- Recovery never recreates raw provider/test content.
- Concurrent identical resume requests converge to one progress event.
- Long Windows-like runtime paths remain bounded through deterministic request/session identifiers.
- Read-only health inspection and operator handoff expose continuity/status evidence without private project paths or authority expansion.

## Deterministic evidence

`tools/v1256_6_8_persistent_development_session_reliability_tests.py`: **36/36 passed**.
