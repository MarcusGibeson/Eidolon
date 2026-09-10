# Desktop Codex Handoff: Eidolon v1268.9

## Review target

Validate the Operator Review Handoff on native Windows using the final source-only candidate.

## Native checks

1. Create a real disposable v1265 self-candidate and verify v1266/v1267 lineage reaches v1268.
2. Confirm review changed paths are readable while source contents/raw provider/test output remain excluded.
3. Confirm exact packet-bound approve/defer/reject semantics and idempotent replay across process restart.
4. Race review disposition from multiple processes/tabs and confirm exactly one compatible result.
5. Change active source after review preparation and confirm freshness blocks v1269 consideration.
6. Change the disposable candidate after review preparation and confirm freshness blocks v1269 consideration.
7. Exercise real NTFS junction/reparse-point and case-insensitive path conditions around the candidate/runtime roots.
8. Exercise long Windows runtime paths.
9. Confirm approve-for-v1269-consideration does not mutate active source or grant self-update/application authority.
10. Confirm v1255 remains the separately governed application boundary and v1269 still requires a fresh preflight/authorization.

## Expected boundary

v1268 is review only. No installation, release, active-source mutation, permanent approval, or independent self-update authority exists at this checkpoint.
