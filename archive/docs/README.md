# Eidolon Historical Documentation Archive

This directory retains superseded documentation and milestone evidence outside the active development surface.

Historical material is not discarded. `DOCUMENT_ARCHIVE_MANIFEST.json` records the original path, archived path, byte size, and SHA-256 for every artifact moved by the documentation cleanup campaign.

## Policy

- Repository-root documentation is limited to the canonical project, next-steps, and release-history ledgers.
- `docs/` contains only documentation or metadata still required by current source, verification, compatibility, or operator procedures.
- Completed roadmaps, bundle reviews, validation reports, handoffs, checkpoint ledgers, and other historical evidence belong here once executable path dependencies are redirected.
- Archived content is evidence, not an active runtime or authority surface.
- Historical files remain byte-preserved unless a future explicit migration changes the archival format with its own verification evidence.

## Navigation

- `DOCUMENT_ARCHIVE_MANIFEST.json`: authoritative move and hash ledger.
- `root_history/`: documents that were already safe to retire from repository root in the first cleanup pass.
- `release_history/`: superseded release-validation artifacts.
- `legacy_dependencies/`: historical root documents whose executable references were deliberately redirected during the second cleanup pass.
- `active_retired/`: completed roadmap/ledger material retired from `docs/` after dependency analysis.
