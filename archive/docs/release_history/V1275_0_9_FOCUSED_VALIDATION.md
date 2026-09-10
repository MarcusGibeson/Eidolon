# v1275.0-v1275.9 Focused Validation

v1275 adds deliberate dependency and reproducible package management above v1274 Environment Awareness without weakening the existing supervised execution/update boundaries.

## Focused suites

- `tools/v1275_0_2_dependency_packaging_foundations_tests.py` — 93/93
- `tools/v1275_3_5_dependency_packaging_integration_tests.py` — 26/26
- `tools/v1275_6_8_dependency_packaging_reliability_tests.py` — 86/86
- `tools/v1275_9_dependency_packaging_checkpoint_tests.py` — 13/13

## Key demonstrated properties

- recursive requirements includes remain path-contained and bounded;
- normalized dependency intent is fingerprinted without persisting raw file contents;
- incompatible pins, contradictory bounds, and direct-reference/spec overlaps are blocked;
- lock/configuration intent is represented by path/size/digest evidence;
- dependency-change plans do not modify source and are not install authority;
- clean-install preflight is bound to current observed v1274 environment evidence;
- generic approval does not authorize installation;
- exact clean-install authorization is digest-bound and invalidated by dependency-intent drift;
- the default install path creates a disposable virtual environment and forces `--no-index`/`PIP_NO_INDEX=1`;
- raw installer output is not persisted;
- source-only package manifests reuse established privacy/inclusion rules;
- deterministic ZIPs use one `Eidolon/` root, fixed metadata, and byte-identical repeated builds;
- package reproducibility does not publish or release the candidate;
- v1274 and all lower authority boundaries remain authoritative.

Final aggregate results are recorded in `Eidolon_v1275_9_FINAL_VALIDATION.md` after retained verification and fresh-extraction parity.
