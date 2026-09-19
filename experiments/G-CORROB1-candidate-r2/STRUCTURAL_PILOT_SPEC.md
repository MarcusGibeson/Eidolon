# G-CORROB1-R2 future structural-pilot specification

**SPECIFICATION ONLY. NO PILOT IMPLEMENTATION OR EXECUTION EXISTS.**

The eventual pilot uses deterministic stubs and synthetic IDs `SX*` that are not
present in the r2 corpus. It tests mechanics only and never changes semantic prompt,
gold, sampling, comparison, metrics, or gates.

## Required fixed fixtures

| Fixture | Stub output / condition | Required mechanical result |
|---|---|---|
| SX01 | valid `supports/match/compatible/high` with anchored quote | structurally valid; G10 `use` |
| SX02 | valid `partial/match/compatible/high` | structurally valid; G5 `investigate` |
| SX03 | valid `contradicts/match/compatible/high` | structurally valid; G2 `abstain` |
| SX04 | malformed JSON returned once | one contact; structural rejection; no repair/retry |
| SX05 | syntactically complete record flagged truncated | structural rejection with `truncated_output` |
| SX06 | wrong proposition/evidence bindings | structural rejection with both binding reasons |
| SX07 | quote absent from passage | structural rejection with grounding reason |
| SX08 | otherwise valid object containing `disposition` | structural rejection for forbidden authority field |
| SX09 | A=`use`, B=`investigate` | paired `investigate`; A/B traces preserved |
| SX10 | A=`use`, B=`abstain` | paired `abstain`; A/B traces preserved |
| SX11 | A=`use`, B=`use`, synthetic gold forbids use | paired `use`; scorer reports one correlated false-clean and one unsafe use |
| SX12 | second scheduled provider call raises after contact | exact contact counted; run infrastructure-incomplete; no third call or retry |
| SX13 | telemetry persistence throws | scientific outputs equal telemetry-off control; content-free degradation warning |
| SX14 | scorer denominator fixture with duplicate repeat ID | scorer self-test rejects duplicate; no aggregate result |

## Pilot pass conditions

- Every fixture produces its exact expected validation reasons, individual rule,
  paired result, accounting, and terminal category.
- Provider attempts/contacts equal the synthetic schedule exactly.
- No prompt, output, gold, semantic label, disposition, or scorer result appears in
  Activity telemetry.
- Telemetry on/off scientific artifacts are byte-identical.
- No candidate corpus item or model-generated semantic observation is consumed.
- No model/provider call occurs.

Any mismatch is a mechanical pilot failure under `ABORT_RULES.md`. Repair requires
a new implementation candidate, hashes, and audit before another pilot.
