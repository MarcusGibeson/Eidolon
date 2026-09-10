# v1201.0-v1201.2 Isolated Workspace Materialization Review

Validated provider output can now be transactionally materialized only inside a revision-bound external workspace. Selected projects are copied from the exact inspected snapshot, generated changes are applied to staging, all file digests and budgets are checked, and the staging directory is atomically promoted. Resume verifies both the sealed record and every workspace file.

No command or test execution occurs. The selected project, Eidolon source, models, and release state remain unchanged. Public state contains digests and counts, never paths, filenames, or generated contents.
