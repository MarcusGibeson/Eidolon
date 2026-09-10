# Desktop Codex Handoff: v1265.9 Isolated Self-Modification

## Candidate purpose

Review v1265's claim that a validated v1264 mutation-capable plan can create and mutate a clean source-only copy of Eidolon while the active Windows installation remains untouched.

## Native Windows checks requested

1. Materialize the full source-only self workspace on NTFS under a normal long user path.
2. Confirm actual junctions, symlinks, and reparse points anywhere in source or candidate containment are rejected.
3. Confirm case-insensitive aliases/collisions cannot produce duplicate or escaped candidate paths.
4. Exercise paths beyond 260 characters with long-path support enabled and disabled where applicable.
5. Launch concurrent exact authorizations from separate processes/tabs and confirm one provider operation / one sealed candidate.
6. Change the active source between preparation and authorization and confirm provider contact is blocked.
7. Tamper with the disposable candidate after sealing and confirm review validation fails.
8. Interrupt during provider-backed mutation and confirm v1265 does not auto-retry or apply a partially known candidate.
9. Attempt private/runtime paths (`data/`, caches, logs, provider payloads, memories, approvals, secrets) and confirm none enter the clean copy or candidate.
10. Confirm cleanup cannot traverse outside the operation workspace.

## Authority review

Confirm v1265 does not provide an alternate route around v1255 application authority. The candidate must remain external and review-only. Installation, promotion, certification, release, permanent approval, and independent self-update authority remain false.

## Known limitations

- v1265 structurally parses changed Python files but intentionally does not choose or run project regressions; v1266 owns test selection.
- Interrupted provider work fails closed and requires operator re-prepare; transparent long-running recovery is not claimed here.
- Release validation uses deterministic provider callbacks, not a native provider.
- No semantic proof is claimed that a candidate preserves all behavior merely because its changed Python parses.

Next bounded unit after accepted review evidence: **v1266 Intelligent Test Selection**.
