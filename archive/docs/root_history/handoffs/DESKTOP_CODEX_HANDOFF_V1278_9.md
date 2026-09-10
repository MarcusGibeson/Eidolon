# Desktop Codex Handoff — v1278.9 Security and Privacy Hardening

## Candidate focus

Validate v1278 security/privacy hardening on native Windows against the real v1255/v1269/v1275/v1277 governed development lineage. Synthetic Python fixtures are evidence, not a substitute for NTFS/reparse/process behavior.

## Native checks

1. Attempt source/package traversal using `..`, absolute, drive-relative, alternate-separator, ADS, trailing-dot/space, reserved-device, case-collision, and extended-length path shapes.
2. Create NTFS symlinks and junctions at source root, intermediate directories, candidate directories, and package inputs. Confirm scans/package reads/update/application fail closed without dereferencing external targets.
3. Swap an intermediate parent to a junction/reparse target between preflight and the immediately-before-write revalidation. Confirm the mutation is blocked when the swap is visible at the recheck.
4. Exercise NTFS sharing violations and locked targets during governed apply/update/rollback and verify rollback/recovery preserves authority boundaries.
5. Test drive-letter, UNC, `\\?\` extended-length, and >260-character paths.
6. Exercise Windows reserved device names and alternate data streams without writing outside the disposable fixture.
7. Run Defender/indexer contention against candidate/source/archive reads and atomic replacement paths.
8. Inspect malicious ZIPs containing traversal, absolute/drive-like names, backslash ambiguity, casefold collisions, symlink external attributes, encrypted members, oversized metadata, and suspicious compression ratios. Never extract an archive that fails structural inspection.
9. Place secret-like files outside the source and expose them only through symlink/junction/reparse paths. Confirm secret scanning reports metadata only and never reads/returns the target secret.
10. Verify provider payloads/prompts/responses/credentials never appear in security receipts, observability, release evidence, or source-only archives.
11. Verify source and runtime roots cannot overlap or become linked through reparse behavior.
12. Re-run exact authorization tests for controlled application, governed self-update, rollback, provider mutation, and trusted-test execution after native path hardening.

## Known limitations

- Immediate pre-mutation path revalidation narrows TOCTOU exposure but is not equivalent to OS-handle/descriptor-based race elimination.
- Cross-machine/network-filesystem trust and distributed filesystem semantics are outside v1278 scope.
- Malicious archive validation is structural and source-package focused; v1278 is not a general-purpose archive sandbox.
- Security evidence grants no command, provider, test, mutation, install, application, update, rollback, promotion, certification, release, permanent, or autonomous authority.
- v1279 Operator Experience has not been started.
