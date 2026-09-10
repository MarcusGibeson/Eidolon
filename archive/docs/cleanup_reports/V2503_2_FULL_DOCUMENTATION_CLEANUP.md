# v2503.2 Full Documentation Surface Cleanup

This source-only checkpoint completes the bounded documentation active-surface consolidation begun after v2503.2.

## Result

- Repository-root Markdown reduced from 134 files in the prior cleanup candidate to 3 canonical files: `README.md`, `README_NEXT_STEPS.md`, and `README_RELEASE_HISTORY.md`.
- Active Markdown under `docs/` reduced from 59 files to 16 files that remain required by current source, verification, compatibility, or operator procedures.
- Active Markdown surface reduced from 193 files to 19 files.
- 184 additional historical artifacts were retired after the first cleanup candidate, bringing the archive move ledger to 1,084 byte-preserved moves total.
- Legacy checkpoint, validation, handoff, bundle-review, roadmap, and ledger path dependencies were redirected to `archive/docs/` rather than preserved at obsolete root paths.
- Completed/unreferenced roadmap and ledger material was retired from active `docs/`.
- `docs/README.md` is a compact index of the remaining active documentation/reference surface.
- `archive/docs/README.md` documents archival policy and navigation.

## Integrity

Every moved artifact is listed in `archive/docs/DOCUMENT_ARCHIVE_MANIFEST.json` with original path, archived path, byte count, and SHA-256. Final audit found 1,084 manifest entries, zero missing archived targets, and zero hash mismatches.

## Verification

- `tools/v2503_2_candidate_specific_evidence_follow_up_tests.py`: 25/25 pass.
- `tools/v1250_0_authoritative_cleanup_baseline_tests.py`: 99/99 pass.
- v1474 documentation maintenance foundations: 5/5 pass.
- v1474 documentation maintenance integration: 7/7 pass.
- v1474 documentation maintenance reliability: 7/7 pass.
- v1474 documentation maintenance checkpoint: 7/7 pass.
- Python source compilation passed through the bounded quick release verifier.
- Version inventory passed through the bounded quick release verifier.
- The broad quick verifier did not complete within the available execution window; it reached its corrective suite after those two passes, so no full quick-profile pass is claimed.

## Pre-existing verification findings

The older v1202.9 JavaScript checkpoint suite fails identically in the untouched prior cleanup candidate on its historical dashboard-text assertion. Earlier review also identified checkpoint-registry mapping ambiguity/missing mappings around v2501.1, v2501.9, and v2503.0.1. These are not attributed to the documentation relocation.

## Compatibility decision

`README_NEXT_STEPS.md` and `README_RELEASE_HISTORY.md` remain canonical active ledgers even though they are large. Hundreds of runtime and verifier contracts inspect their exact content. Compacting them safely requires a separate compatibility-ledger migration rather than deleting historical text for cosmetic size reduction.
