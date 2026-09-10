# Eidolon v1250.3-v1250.5 Bundle B Review

## Scope

Bundle B consolidates release metadata, whole-version checkpoint records, and retained historical compatibility markers without adding product capability or expanding authority.

Authoritative input:

- `Eidolon_v1250_2_verification_foundation_bundle_a_final_candidate_source_only.zip`
- SHA-256: `90D67871131CFD765754B2C962229D18DDC043BE06467170BFF93A27A61F2308`

The input archive remained immutable. Work occurred in a separate extracted tree beneath one `Eidolon/` root.

## v1250.3 Release Metadata Consolidation

Added `conscious_agent/release_metadata_consolidation.py` and `docs/release/release_metadata_manifest.json`.

The active release-metadata surface now has three explicit roles:

- `conscious_agent/release_authority.py` is the only active version and roadmap authority;
- `conscious_agent/release_metadata.py` is a generated import-compatible facade;
- `release_metadata.py` is a generated top-level import shim.

The agent facade was reduced from 608 lines of active and historical assignments to a small generated surface with one active working version, one active previous version, one milestone, one next unit, and one inert historical compatibility payload. Exact facade digests are recorded in the metadata manifest.

No facade or manifest authorizes installation, promotion, certification, release, provider contact, project mutation, source mutation, or independent action.

## v1250.4 Checkpoint Registry Consolidation

The checkpoint registry now exposes two deliberately separate read-only views:

1. a 56-record structured release-checkpoint index derived from `CHECKPOINT_HISTORY`, with one test selector and one evidence-only record per whole-version checkpoint from v1200.0 through v1250.5; and
2. the preserved v1150.2 source-discovered builder registry used by historical checkpoint callers and architecture dispatch.

The structured registry adds:

- deterministic checkpoint records;
- exact test-resolution evidence;
- a canonical read-only checkpoint report schema;
- digest-bound reports and validation;
- explicit zero-authority fields;
- checkpoint reports for v1250.3, v1250.4, and v1250.5.

During retained regression testing, the first consolidation draft was found to have replaced the legacy descriptor API. That regression would have hidden more than 300 historical checkpoint builders from retained callers. The final implementation preserves the complete source-discovery API, compatibility aliases, resolver functions, and architecture dispatch behavior while retaining the new structured registry. The v1250.4 suite now verifies both surfaces explicitly.

The final source-discovered registry exposes 318 descriptors with no duplicate checkpoint identifiers or builder targets.

## v1250.5 Compatibility Registry Migration

Added `conscious_agent/compatibility_registry.py` and `docs/compatibility/release_metadata_compatibility_registry.json`.

The registry contains 519 ordered historical marker records recovered from the v1250.2 metadata facade. Every entry records:

- ordinal;
- source line;
- marker category;
- exact text;
- SHA-256 digest.

The registry validates ordering, uniqueness, category counts, source-facade lineage, exact historical reconstruction, generated-facade parity, and authority boundaries. The original v1250.2 facade remains preserved under `docs/legacy/release_metadata_v1250_2_facade.py.txt`.

Historical text is retained for old tests, but it is inert and cannot override the active release authority.

## Verification corrections

The v1250.0 documentation test previously required every active README to display `v1250.2`, even after the working version advanced. It now validates document-specific semantic lineage instead:

- the main README names Bundle A as the previous bundle;
- next steps names the completed Bundle B and upcoming Bundle C;
- release history contains the structured v1250.2 and v1250.5 records;
- the roadmap records Bundle A and Bundle B in order.

This removes a stale prose-token dependency without weakening release-history validation.

## Verification evidence

Focused cleanup suites:

- v1250.0 authoritative cleanup baseline: 99/99 passed;
- v1250.1 segmented broad verifier: 101/101 passed;
- v1250.2 hermetic verification runtime: 98/98 passed;
- v1250.3 release metadata consolidation: 102/102 passed;
- v1250.4 checkpoint registry consolidation: 114/114 passed;
- v1250.5 compatibility registry migration: 100/100 passed.

Retained regression evidence:

- v1150.2 checkpoint consolidation and architecture dispatch: 25/25 passed;
- v1249.0-v1249.2 foundations: 195/195 passed;
- v1249.3-v1249.5 review and interface stability: 266/266 passed;
- v1249.6-v1249.8 adversarial reliability: 183/183 passed;
- v1249.9 checkpoint: 53/53 passed.

Segmented verifier evidence:

- `retained-checkpoints` passed all seven suites from a clean external snapshot;
- `source-privacy` passed both suites from a clean external snapshot;
- both stages reported zero source-snapshot runtime debris;
- both stages preserved the authoritative source tree;
- runtime cleanup completed successfully.

Additional evidence:

- all-source disposable-cache compile passed;
- no source-tree bytecode was written;
- no runtime `data/`, cache, VCS, archive, credential, or private-state entry remains in the candidate tree;
- secret-pattern matches are limited to explicit scanner constants and synthetic test canaries;
- the v1250.2 input archive SHA-256 remained unchanged.

## Explicit non-claims

Bundle B does not claim:

- a complete ten-stage broad-verifier pass;
- completion of oversized-module decomposition;
- removal of every historical compatibility token;
- installation readiness;
- promotion, certification, publication, or release readiness;
- Desktop Codex approval;
- provider or native-runtime review;
- independent or autonomous authority.

## Next bounded unit

`v1250.6-v1250.8 Architecture Consolidation and Oversized Module Decomposition Bundle C`
