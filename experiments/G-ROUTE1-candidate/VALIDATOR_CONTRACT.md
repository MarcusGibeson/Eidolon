# G-ROUTE1 validator contract

**Status:** candidate pending deterministic audit and freeze. No runner, provider call, routing decision, or production authority exists.

## Separation

`corpus.json` and `prompt_profiles.json` are model-facing candidate artifacts. `gold.json` is evaluator-only and must never enter a model request. The same fixture and prompt-profile bytes apply to the small, mid, and large candidates.

The validator returns deterministic hard-gate evidence. It does not select a model, grant routing authority, modify settings, retry a provider call, repair output, or create belief effects.

## Profiles

### `conversation.v1`

The result is plain text. Frozen checks cover required factual anchors, at least one acceptable phrase from each alternative group, forbidden action claims, and a maximum length. These fixtures measure bounded response discipline, not subjective prose quality.

### `extraction.v1`

The result is one JSON object. Keys and values must exactly match evaluator-only gold. Missing, extra, inferred, or mistyped fields fail.

### `research.v1`

The result has exactly `claims`, `recommendation`, and `uncertainties`. Claim identity, support status, source IDs, independent lineage IDs, recommendation, and uncertainty codes are compared after order normalization. Duplicate citations or lineage IDs fail. Vendor repetition cannot manufacture independent support.

### `synthesis.v1`

The result has exactly `statements` and `conclusion`. Every observation must be represented once. A statement may merge only observations with the same semantic role. Role changes, silent drops, duplicate coverage, unknown IDs, lost meaning anchors, and conclusion drift fail.

### `coding.v1`

The model result has exactly `path`, `old`, and `new`. The path and exact source anchor are bound to the fixture. The validator constructs the candidate in memory but **does not execute model-produced code**.

Compile and focused-test results must come from a separately governed isolated runner under `g-route1.isolated-fixture-runner.v1`. Its evidence must bind the fixture ID, candidate digest, focused-test digest, isolation status, compile result, test result, exit code, and test count. Missing or mismatched evidence fails closed. Building that runner is a later phase and is not authorized by this freeze.

### `planning.v1`

The result has exactly `steps`, `uncertainties`, `claims_completed`, and `requested_authority`. Evidence binding, dependencies, uncertainty, non-completion, and no-authority constraints are exact. Fabricated completion or authority expansion fails.

## Element types in model-supplied lists

Wherever the contract requires a list of text — `uncertainties`, `citations`, `lineages`,
`observation_ids`, `evidence_ids`, `depends_on` — a model may instead return objects, nested lists, or
no list at all. That is a model-produced failure and is classified as one, in both the gold-blind
operational validator and the evaluator, under `*_element_type_mismatch`. The non-text element is
excluded from de-duplication and identity lookups; it is never stringified into a shape that could
pass, and it never raises.

This rule exists because it was once violated. R2 halted at schedule position 57 when a structurally
legal answer carried objects in `uncertainties` and the evaluator de-duplicated with `set()`. A wrong
answer must be scored, not crash the benchmark.

## Hard boundaries

- No aggregate result can erase a failed fixture/repeat hard gate.
- R4 fixtures produce qualification evidence only; adaptive R4 selection remains prohibited.
- Gold and validator success do not authorize a benchmark, model call, production router, escalation, provider change, source apply, or belief effect.
- Malformed output is an observed failure. There is no validator repair or retry.
- Candidate identity is absent from prompts.
