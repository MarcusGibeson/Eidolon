# Desktop Codex Handoff: v1269.9 Governed Self-Update

## Candidate purpose
Validate the native Windows behavior of the v1269 governed self-update boundary before v1270 integration.

## Highest-value native checks
1. Run the exact v1268 review -> v1269 preflight -> exact authorization flow on a disposable Windows Eidolon installation.
2. Confirm the private backup is captured immediately before the first active-source write.
3. Confirm only reviewed paths change and unrelated operator edits are preserved or cause a stale full-source block rather than being overwritten.
4. Exercise real NTFS atomic replacement semantics, case-insensitive aliases, long paths, and junction/reparse containment.
5. Interrupt the process before the first write, during a known partial multi-file write, after the candidate manifest is installed, and during restart/health verification.
6. Confirm an expired known-partial operation restores the backup before same-authorization recovery; unknown/conflicting affected-path state must fail closed.
7. Use an external supervisor to restart Eidolon after update and verify defined startup/import/dashboard/API health signals.
8. Force post-update health failure and confirm automatic rollback restores the prior manifest before control returns.
9. After a successful update, verify rollback requires a separate exact rollback authorization.
10. Race duplicate update authorization from separate Windows processes/tabs and verify exactly-once mutation.

## Authority assertions
- v1268 approve-for-consideration is not self-update authority.
- v1269 authorization is exact, one-time, review/candidate/source bound, and non-transferable.
- No promotion, certification, release, permanent approval, or independent future self-update authority is created.
- v1255 remains the separately governed general application/rollback boundary.

## Known environment limitation
The development environment can validate transactional file behavior and a fresh-child-process health signal, but it cannot prove real Windows service/process replacement or NTFS junction/reparse behavior. Those remain explicit Desktop checks.
