# v2503.4.39 Training Evidence Operatorization Handoff

## Completed

The v2503.4.31-v2503.4.39 operatorization arc is consolidated in this checkpoint. Ordinary verified coding/repair and bounded research workflows now resolve a durable operator capture policy, create raw evidence automatically, and run deterministic sanitization when enabled. Planning and deterministic governance outcomes have bounded adapters. Capture or sanitation failure never changes a successful underlying task and is reported through a runtime-only failure receipt.

The Dashboard Settings surface and both local API surfaces expose capture policy and status. The training dataset CLI adds status, record inspection, readiness, immutable dataset creation, frozen evaluation corpus creation, artifact listing, benchmark status, and explicitly authorized configured local-model benchmarking.

## Fresh And Migrated Defaults

- Verified coding/repair capture: on
- Verified research capture: on
- Verified planning capture: on
- Deterministic tool/governance capture: on
- Ordinary conversation capture: off
- Automatic sanitization: on
- Automatic approval: off
- Automatic dataset export: off
- Model training authority: off
- Model promotion authority: off

An existing installation that lacks the training settings receives these explicit safe defaults on its next settings load. Existing unrelated settings remain unchanged.

## Operator Paths

Use Dashboard Settings to change capture categories. Status is available at `/api/training-evidence/status`; policy updates use `/api/training-evidence/settings` and accept only the six capture-policy keys.

CLI inspection examples:

```text
python tools/eidolon_training_dataset.py status
python tools/eidolon_training_dataset.py readiness
python tools/eidolon_training_dataset.py list-raw
python tools/eidolon_training_dataset.py list-sanitized
python tools/eidolon_training_dataset.py list-approved
python tools/eidolon_training_dataset.py list-datasets
python tools/eidolon_training_dataset.py list-eval-corpora
python tools/eidolon_training_dataset.py benchmark-status
```

Dataset creation, evaluation-corpus creation, and benchmarking retain explicit confirmation. None of these commands approves records, exports training data, trains a model, registers a candidate, or promotes a model.

## Acceptance

The native operator acceptance suite proves automatic coding and research capture, sanitation without approval, disabled capture, non-fatal capture failure receipts, preference-pair generation, immutable/idempotent dataset and evaluation workflows, configured-provider benchmark accounting, status surfaces, Dashboard controls, and CLI commands.

## Remaining Limits

Ordinary conversation capture remains intentionally disabled. Planning and governance capture is limited to workflows with deterministic outcome validation. Benchmarking requires a pre-existing frozen corpus and the exact configured provider/model. Corpus readiness remains governed by the existing 5,000 approved-example and 500 frozen-evaluation thresholds; this release does not claim readiness unless that gate passes.

## Next Roadmap Unit

v2503.5 - Targeted Candidate-Specific Evidence Discovery.
