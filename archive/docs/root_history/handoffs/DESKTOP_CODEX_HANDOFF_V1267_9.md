# Desktop Codex Handoff: Eidolon v1267.9

## Candidate

v1267.9 Iterative Self-Repair Checkpoint. Source-only development candidate; not installed, promoted, certified, released, or self-applied.

## Review focus

1. Verify v1265 still copies source-only Eidolon into external runtime storage and never includes `data/` or private runtime state.
2. Verify v1266 selection remains bound to the exact candidate and trusts only active-baseline tests.
3. Exercise v1267 exact repair authorization with zero/incorrect/correct authorization text.
4. Confirm selected tests run against the disposable candidate and trusted test files are unchanged from active source.
5. Exercise one-repair success and a genuinely changed-failure two-repair success.
6. Confirm the same normalized failure blocks before another provider call.
7. Confirm provider failure and provider-pending restart never auto-retry.
8. Confirm a repair attempting to modify/delete a trusted test fails closed.
9. Change active source after repair preparation and verify v1267 blocks before provider contact.
10. Exercise actual NTFS long paths, case-insensitive aliases, junctions/reparse points, and cross-process duplicate repair attempts.
11. Interrupt during selected-test execution, immediately before provider return, after provider return/before candidate transaction, and after repair/before rerun verification.
12. Confirm active Eidolon source remains byte-identical throughout all disposable repair scenarios.

## Known boundary

Selected trusted tests execute in bounded subprocesses against the disposable candidate. This is not claimed as an OS-enforced Windows sandbox. Review should treat native process/network containment as a separate platform/security concern rather than inferring it from source isolation.

## Next bounded unit

v1268 Operator Review Handoff. Do not start v1269 Governed Self-Update from this candidate without completing v1268 and retaining separate operator authority.
