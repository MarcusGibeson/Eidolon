# Desktop Codex Handoff: v1266.9 Intelligent Test Selection

## Review objective

Verify on native Windows that one sealed v1265 isolated self-candidate produces the same bounded v1266 focused/regression selection without executing tests or changing either active source or the disposable candidate.

## Native Windows checks

1. Create the same candidate beneath a normal NTFS path and beneath a long-path workspace.
2. Exercise actual NTFS junction/reparse entries around source and test directories; containment must fail closed.
3. Exercise case-insensitive aliases/collisions for trusted test paths.
4. Run simultaneous selection requests from separate processes/tabs; they must converge on one deterministic record.
5. Change the candidate after selection and verify freshness invalidates the selection.
6. Modify/delete a trusted baseline test in a disposable candidate and verify selection is blocked.
7. Add a provider-created candidate test and verify it is supplemental/untrusted rather than retained evidence.
8. Change a high-risk self-modification/governance module and confirm regression expansion includes the expected retained boundaries.
9. Confirm selection itself launches no provider, command, test process, or package manager.
10. Confirm the active Eidolon tree is byte-identical before/after selection.

## Authority boundary

Application remains separately governed by v1255. v1266 has no test-execution, repair, active-source application, installation, release, permanent approval, or independent self-update authority.

## Next bounded unit

`v1267 Iterative Self-Repair` may consume an exact fresh v1266 selection and separately govern test execution/repair. It must not reinterpret v1266 selection as application or release authority.
