# Windows/Desktop Codex Handoff: v1197.9

## Candidate purpose

Review the read-only v1197.9 Runtime Migration, Backup, Upgrade, Rollback, and Fresh-Install checkpoint. This candidate consolidates lifecycle foundations, operator-reviewed application evidence, and reliability/adversarial evidence without reading or changing runtime data.

## Required Desktop checks

1. Verify the candidate ZIP SHA-256 against the value supplied with the release.
2. Extract beneath exactly one clean `Eidolon/` root in a neutral path that does not share a candidate-version cleanup prefix.
3. Confirm source-only privacy and absence of runtime, settings, cache, bytecode, private evidence, or workspace artifacts.
4. Run `tools/v1197_9_runtime_lifecycle_checkpoint_tests.py` with UTF-8 and `PYTHONDONTWRITEBYTECODE=1`.
5. Run the three retained v1197 bundle suites.
6. Run the retained v1196.9 through v1189.9 checkpoint stack.
7. Run `tools/v1150_1_external_runtime_data_migration_tests.py` and `tools/v1150_1_source_only_runtime_boundary_tests.py` with `PYTHONPATH=.` where required.
8. Compile all Python source into a neutral external bytecode directory.
9. Exercise the `runtime-lifecycle-checkpoint` CLI and GET-only API endpoint.
10. Confirm POST is unavailable and no runtime directory is created or changed.

## Expected checkpoint truth

- Five lifecycle operations.
- Five review actions.
- Three decisions and fifteen reviews.
- Eight reliability event classes.
- Original runtime, backup, rollback, and fresh-install isolation preserved.
- Foreground available and recovery review required.
- No runtime read, backup creation, migration, upgrade, rollback, installation, recovery, retry, approval consumption, provider/model contact, process/thread start, mutation, release, global-pass claim, or authority grant.

## Windows-specific attention

- Use explicit UTF-8 text reads.
- Keep runtime and bytecode output outside the extracted source tree.
- Use neutral paths to avoid the inherited cleanup-prefix tooling issue.
- Verify that no CRLF normalization changes source or digest evidence.

## Decision boundary

This is not the v1200 decision gate. Reaching v1197.9 does not install, promote, certify, publish, release, or grant independent authority. The next bounded unit is v1198.0-v1198.2 Feature Freeze and Architecture Consolidation Foundations.
