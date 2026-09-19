# G-CORROB1-R2 R22 prospective semantic repair

**Status:** pre-provider-contact corpus revision; no model observation, pilot,
execution, gold-label change, policy change, or threshold change.

## Exact change

Before:

> Mixer M completed its sanitation cycle on 2032-08-02.

After:

> Mixer M completed sanitation cycle S-44 on 2032-08-02.

The evidence is unchanged:

> Mixer M's final controller record for 2032-08-02 marks sanitation cycle S-44
> aborted before completion and records no later sanitation cycle.

## Rationale

The failed pre-pilot audit correctly found that the old proposition did not bind
its event to S-44. Aborting S-44 and recording no later cycle did not rule out an
earlier completed cycle, so the evidence could not contradict the unbound claim.

The repair narrows the proposition to the event the evidence actually identifies.
It adds no premise about S-44 being the only cycle that day. No other corpus item
was changed.

## Fresh R22 assessment

- Relation: `contradicts`. The evidence explicitly records S-44 as aborted before
  completion, which entails that S-44 did not complete.
- Scope: `match`. Proposition and evidence identify the same mixer, cycle S-44,
  and date.
- Temporal status: `compatible`. The controller record addresses the asserted
  date directly.
- Quantifiers: none.
- Qualifiers: the cycle identifier and date match exactly.
- Conjunction behavior: none; the proposition is a single event claim.
- Operational eligibility: `abstain`; the evidence cannot be cited as support
  for the contradicted proposition.

The existing R22 gold tuple remains semantically correct after this independent
reassessment; it is not retained merely for compatibility.
