# G-CORROB1-R2 execution-freeze candidate audit

**Verdict:** `READY FOR OPERATOR REVIEW BEFORE STRUCTURAL PILOT`

This audit covers the repaired, renewed-signoff execution-freeze candidate only.
It grants no pilot, provider-generation, or experiment authority.

## Candidate identity

- Implementation commit bound: `66ee6d90696778d631239ee944dad611b583195f`
- Blocking-audit checkpoint bound: `5cfae23c1e2d3a3e52dc92c4dec0cb13eb5a44ac`
- Corpus SHA-256: `2e95bcdef81e1303637ec581b2ff09dfdd9421d9f1742f780d8771ffcf5bc60a`
- Gold SHA-256: `54f33df4b73ea13d5bc945afe763777802c8bd0ebb603ebfba20c78aed20bd6f`
- Implementation-candidate file SHA-256:
  `8e4bfec2d802eba1d2ba7358f7f2bb7083643d9288af95581a57d7474795db84`
- Execution-freeze-candidate file SHA-256:
  `366a787cbf901f25e795d72ad4f71bd09a1f5318a51ed6549940bc9c3aff5114`
- Embedded execution-freeze content SHA-256:
  `21b2c333c28289d81ecc7943a5ec637f6972cae5120bdacd5b800237904d9434`
- Model manifest SHA-256:
  `22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643`

The manifest records `execution_frozen=true` as artifact immutability, while
`execution_authorized=false`, `pilot_authorized=false`, and
`experiment_authorized=false`. The runner rejects this candidate even if wrapped
in a fabricated execution confirmation because the manifest is not an authorized
execution manifest.

## Adversarial freeze review

| Attack | Deterministic proof | Result |
|---|---|---|
| Corpus drift | Bound corpus digest mutation | Rejected. |
| Gold/ambiguity drift | Bound gold digest mutation | Rejected. |
| Prompt drift | Bound prompt digest mutation | Rejected. |
| Individual-policy drift | Bound policy digest mutation | Rejected. |
| Comparator drift | Comparator shares the bound policy module; digest mutation | Rejected. |
| Scorer drift | Bound scorer digest mutation | Rejected. |
| Denominator drift | Bound metrics definition mutation | Rejected. |
| Threshold drift | Bound threshold-provenance mutation | Rejected. |
| Provider/config drift | Preflight artifact and top-level configuration digest mutation | Rejected. |
| Model digest/version drift | Live-receipt-to-manifest binding mutation | Rejected. |
| Seed/order drift | Bound sampling/contract artifact mutation | Rejected. |
| Activity side-channel drift | Activity adapter is bound; allowed metrics exclude semantic/evaluation fields | Rejected or unavailable to telemetry. |
| Persistence drift | Persistence schema is bound | Rejected. |
| Stale-run contamination | Existing run identity reopened with exclusive create | Rejected. |
| Manifest omission | Required top-level field removed | Rejected. |
| Incorrect artifact digest | Any behaviorally relevant digest changed | Rejected. |
| Pilot authorization injection | `pilot_authorized=true` | Rejected. |
| Experiment authorization injection | `experiment_authorized=true` | Rejected. |
| Candidate used as execution manifest | Runner authorization check | Rejected. |

## Gold and provider review

The renewed independent audit re-read all 32 items. Twenty-eight crisp items have
one defensible tuple; four genuine ambiguity diagnostics remain outside crisp
accuracy and primary utility denominators. R22 now names S-44, and its unchanged
evidence directly contradicts completion of that same cycle.

Ollama `0.34.0` resolves `qwen3.8:27b` to the frozen local manifest digest.
All experiment options are bound to exact submitted values. Ollama does not
attest internal honoring of each option, and seed behavior was not exercised.
Those are pilot questions, not facts inferred from submission.

## Activity and privacy review

Collection telemetry remains limited to phase, counts, elapsed progress,
structural/grounding failures, provider contacts, and terminal state. It exposes
no corpus text, propositions, semantic answers or labels, dispositions, gold,
safety classifications, or scores during collection. Activity on/off/failure
parity remains covered by the implementation suite.

The shared Activity contract/API suite passed. Native Tcl/Tk rendering remains an
environment limitation because this Python installation lacks usable `init.tcl`;
native rendering is not claimed as tested.

## Test evidence

- Renewed gold/repair guards: `5/5` passed.
- Freeze adversarial attacks: `7/7` passed.
- G-CORROB1 implementation/adversarial suite: `28/28` passed.
- R2 design-integrity checks: `122/122` passed.
- Shared Activity suite: `15/15` passed.
- Historical G-EVID1 contract: `1966/1966` passed.
- Whole candidate manifest verification: valid and non-authorizing.

The first renewed-history guard run had one wording-only assertion failure
(`did not exclude` versus the preserved report's `does not exclude`). The
assertion was corrected; no product or experiment artifact changed in response.

## Integrity and stopping boundary

- G-EVID1 files and verdict are unchanged.
- Metadata-only provider queries: `5`.
- Semantic generation calls: `0`.
- Structural/mechanical pilots launched: `0`.
- Experiments launched: `0`.
- Belief effects: `none`.

## Unresolved limitations

1. Ollama does not attest internal honoring of every submitted option.
2. Seed behavior and request capture require an explicitly authorized mechanical
   pilot.
3. Native Activity rendering should be rerun in a Tcl/Tk-capable environment.

These limitations do not invalidate the freeze candidate, but they prevent any
claim that the pilot has already verified runtime behavior.
