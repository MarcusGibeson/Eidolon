# G-CORROB1-R2 mechanical pilot attempt 1 blocker

**Result:** `MECHANICAL PILOT REQUIRES REPAIR`

**Authorized execution-freeze candidate SHA-256:**
`366a787cbf901f25e795d72ad4f71bd09a1f5318a51ed6549940bc9c3aff5114`

**Source checkpoint:** `0c43df9be31b614e0eb289efb36e69376d5dcbcf`

## Pre-launch verification

The authorized candidate file hash and source checkpoint matched exactly. The
working tree contained only the pre-existing unrelated
`.codex-remote-attachments/` path. No experiment artifact had drifted.

## Mechanical blocker

The frozen checkpoint contains no live tiny-pilot implementation:

1. `STRUCTURAL_PILOT_SPEC.md` explicitly specifies deterministic stubs, synthetic
   `SX*` identities, and **no model/provider call**.
2. `g_corrob1_runner.execute` always obtains the complete frozen schedule through
   `build_schedule`, records `EXPECTED_CALLS=192` and `EXPECTED_PAIRS=96`, and
   refuses to score until all 96 pairs exist.
3. `g_corrob1_scorer._validate_units` rejects any input other than 192 calls and
   96 pairs with `fixed_observation_or_pair_denominator_mismatch`.
4. No separately frozen pilot runner exists that can make exactly one blind A/B
   pair traverse request construction, live generation, validation, governance,
   comparison, pilot-safe scorer plumbing, persistence, Activity, and terminal
   reconstruction.

Consequently, the authorized two-call live mechanical pilot cannot be executed
through the frozen pipeline. An ad hoc script or in-memory monkeypatch would
bypass the frozen schedule/scorer contract and would not establish the requested
mechanical facts.

## Required prospective repair

A separately governed tiny-pilot harness and revised mechanical-pilot
specification are required. They must:

- use synthetic pilot identities that cannot enter primary experiment metrics;
- make exactly one A/B pair with the frozen request builder and live adapter;
- bind exact role, seed, item, repeat, ordering, and provider configuration;
- use the production parser, structural validator, individual governor, and
  paired comparator unchanged;
- exercise scorer integration without invoking or weakening the production
  192-call denominator or interpreting pilot semantics;
- preserve raw, parsed, validated, governed, paired, telemetry, digest, and
  terminal lineage append-only;
- remain incapable of authorizing or launching the full experiment;
- receive deterministic regression tests, a new implementation audit, renewed
  artifact digests, and a new execution-freeze candidate before another pilot.

No repair was made during this attempt because the authorization required the
pilot to stop on discovery of a genuine mechanical defect.

## Accounting and integrity

- Generation calls: `0`
- Metadata calls during this attempt: `0`
- Pilot launches: `0`
- Full experiment launches: `0`
- Frozen artifacts changed: `no`
- G-EVID1 changed: `no`
- Belief effects: `none`
- Pilot semantic outcomes observed or interpreted: `none`
