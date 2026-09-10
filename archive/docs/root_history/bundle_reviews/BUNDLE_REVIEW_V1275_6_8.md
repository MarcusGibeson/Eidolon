# Bundle Review v1275.6-v1275.8

## Scope

Dependency/package reliability, reproducibility, privacy, and native Windows handoff.

## Implemented

- Lock/configuration intent preservation and drift reporting without exposing file contents.
- Disposable clean Python-environment creation without touching active source.
- Source-only package privacy validation against established forbidden-runtime rules.
- Deterministic ZIP production with sorted source-only entries, fixed archive timestamps/permissions, one `Eidolon/` root, and output containment outside source.
- Independent package builds are byte-identical in deterministic fixtures.
- Native Windows/Desktop Codex scenarios for venvs, pip offline behavior, NTFS locks/sharing violations, long paths, includes, fresh extraction, and reproducibility.

## Authority boundary

Reproducible ZIP creation does not publish or release the package and does not grant installation or dependency-mutation authority.

## Focused evidence

`tools/v1275_6_8_dependency_packaging_reliability_tests.py` — 86/86.
