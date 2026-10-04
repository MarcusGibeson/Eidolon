# Final Targeted Lifecycle Repair

Implementation-only LR1-LR3 closure from blocked audit
`0137bc59db909801ee8b627e578ebdb749d37b54`. Accepted science/corpus
closure remains `6c85b10930cefe410a1965c0924e4fd9f47eb4ef`.

## Boundaries

- LR1: file existence, JSON parsing, exact envelope shape, object payload,
  seal, canonical bytes, safe structural/domain validation, prefix, and exact
  reconstructed state/schedule/binding, in that order. Malformed structures
  use the existing `CORRUPTED_CHECKPOINT` event. Guarded retention is append-only.
- LR2: a transport return is accepted only as a validated plain success object
  or a validated failure object. Unusable outcomes, including exceptions,
  close their START with `FAILURE` and the existing
  `PROVIDER_FAILURE_WITHOUT_RECEIPT`. No arbitrary result is stringified.
- LR3: the exact frozen precontact event catalog drives the existing
  `A_SCHEDULED -> A_BLOCKED` transition for all six A cells before contact.
  Post-contact invalid/incomplete state semantics are unchanged.

The checkpoint-verification lock, B phase-grant boundary, manifest coverage,
all scientific scoring and qualification rules remain unchanged.

## Evidence Plan

`g_extract1_final_lifecycle_tests.py` uses actual Run methods, isolated evidence
copies, sealed malformed checkpoint objects, arbitrary transport values,
post-catch attempts and fresh disk reconstruction. It additionally tests real
prompt-byte corruption, isolated actual byte mutations of the four named
protected files, missing checkpoint marker and fabricated seal, full B
pass/mixed/fail replay, and non-interruption B incomplete/invalid outcomes.

All ten precontact events exercise the integrated guarded verification boundary.
Identity/provider/config cases mutate actual synthetic receipt inputs; the other
seven inject their frozen event at Package.verify rather than changing accepted
artifacts. This tests reporting/retention, not a claim of live provider discovery.

The existing I1-I6 lifecycle suite and complete no-provider pilot remain required.
Two uninterrupted 480-A/240-B synthetic pilots must have byte-identical complete
evidence trees. Socket creation and connection are prohibited during certification.

Both prior blocked candidates remain historical and unactivated:

- `14fb601c3a58777942ccd0361c2a303b5bfcf10d4c05536a32d265c0babe537f`
- `6e7295b3c79ee95930fee7231265e342905b7848d261ae716d1ef1546ca785ab`

A new candidate is created only after successful targeted and full pilot checks.
Exactly one independent read-only implementation audit follows candidate creation.
Any P1/P2 finding stops this task without a post-audit implementation repair.

## Authority

No provider/model contact, real A/B, freeze activation or actual phase grant.
No corpus/gold/design/blueprint/threshold change. Preserved authoring failures and
untracked corpus files stay byte-identical. G-ROUTE4 stays CLOSED FAILED.
Autonomy is false; belief effects are none.
