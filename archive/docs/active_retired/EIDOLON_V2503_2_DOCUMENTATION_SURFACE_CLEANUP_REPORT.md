# v2503.2 Documentation Surface Cleanup Report

This is a non-behavioral source-hygiene cleanup of the authoritative v2503.2 Candidate-Specific Evidence Follow-Up source tree.

## Scope

- Historical evidence was **not deleted**.
- 900 superseded, unreferenced documentation/release artifacts were moved into `archive/docs/`.
- Repository-root Markdown was reduced from 892 files to 134 historical/current files before this report was added.
- `docs/release/` was reduced from 146 files to 4 artifacts that remain referenced by active source or verification.
- `docs/README.md` now indexes the active documentation surface.
- `archive/docs/DOCUMENT_ARCHIVE_MANIFEST.json` records every old path, new path, byte size, and SHA-256 for reversible auditing.
- All Python source files are byte-identical to the supplied v2503.2 baseline. Research behavior, provider authority, installation state, promotion state, and the v2503.3 roadmap are unchanged.

## Verification

- Archive manifest integrity: 900/900 archived files matched their recorded pre-move SHA-256.
- Stale active references to moved paths: 0.
- v2503.2 candidate-specific evidence follow-up: 25/25 passed.
- v1250.0 authoritative cleanup baseline: 99/99 passed.
- v1474 documentation maintenance foundations: 5/5 passed.
- v1474 documentation maintenance integration: 7/7 passed.
- v1474 documentation maintenance reliability: 7/7 passed.
- v1474 documentation maintenance checkpoint: 7/7 passed.
- Quick release verifier: Python compilation and version inventory passed; the corrective suite exceeded the available execution window, so the overall quick profile is not claimed as passed.

## Pre-existing verifier defect

`checkpoint_registry_manifest()` is already blocked in the untouched supplied v2503.2 archive by checkpoint-test resolution errors for v2501.1, v2501.9, and v2503.0.1. A fresh extraction of the original archive reproduced the same errors. Consequently the retained v1250.9 cleanup-hardening checkpoint wrapper fails its `checkpoint_registry_current` assertion both before and after this documentation cleanup. This cleanup deliberately does not alter executable code merely to mask that unrelated historical registry defect.

## Remaining documentation debt

134 root-level Markdown documents remain because current source, tests, compatibility code, or other active artifacts still reference their legacy root paths. The next cleanup step should decouple those hardcoded historical paths before moving the remaining records. The two giant active compatibility documents, `README_NEXT_STEPS.md` and `README_RELEASE_HISTORY.md`, also remain intentionally intact because hundreds of historical tests read exact milestone text from them; trimming them safely requires a separate compatibility migration rather than blind deletion.
