# Desktop Codex Handoff: v1190.2

## Candidate scope

Review only the `v1190.0-v1190.2 Unified Experience Foundations` delta from the verified v1189.9 source-only checkpoint.

## Primary review targets

- `conscious_agent/unified_experience_foundations.py`
- `conscious_agent/unified_experience_foundations_checkpoint.py`
- `tools/v1190_0_2_unified_experience_foundations_tests.py`
- Registry, CLI, GET-only API, dashboard, release metadata, documentation, and release-verifier wiring

## Required checks

1. Confirm exactly one current surface is required for each of the nine experience domains.
2. Confirm duplicate domains, IDs, artifact digests, and receipt digests fail closed.
3. Confirm exact domain order and previous-surface digest lineage.
4. Confirm one and only one focus surface is accepted.
5. Confirm private or authority-bearing fields are rejected.
6. Confirm approval, action, result, and learning state consistency checks remain bounded.
7. Confirm the public projection exposes only content-free states, counts, IDs, and digests.
8. Confirm no approval creation/consumption, execution, continuation, source/runtime mutation, provider/model contact, or authority expansion.
9. Confirm release-verifier registration appears exactly once.
10. Confirm the source-only ZIP contains one `Eidolon/` root and no runtime/private/cache/compiled artifacts.

## Known limitation

The surfaces are caller-supplied digest evidence and are not independently acquired live state. Historical navigation and coordinated cross-surface transitions are intentionally deferred to v1190.3-v1190.5.

## Next bounded unit

`v1190.3-v1190.5 Operator Navigation and Coordinated Experience Transitions`

The next full Desktop Codex and native-provider decision gate remains v1200.
