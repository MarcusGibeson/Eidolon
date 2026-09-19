# G-CORROB1-R2 semantic assessment contract

**Status:** proposed design contract; not an execution freeze and not authority.

The semantic assessor receives one proposition and one passage. It returns only
observable semantic fields. It does not receive or produce gold, safety labels,
operational dispositions, policy decisions, or belief effects.

## Relation

`relation` is the holistic logical relationship between the passage and the
complete proposition in the supplied fictional setting, including all stated
quantifiers, qualifiers, entities, and dates.

- `supports`: the passage entails the complete proposition.
- `contradicts`: the passage entails that the complete proposition is false.
- `partial`: the passage establishes a proper component, conjunct, or strict
  subpopulation of the proposition, but neither the whole proposition nor its
  negation.
- `irrelevant`: the passage has no probative bearing on the proposition.
- `unclear`: the passage is related, but ambiguity or insufficient information
  prevents support, contradiction, or an established proper component.

`partial` is not a synonym for merely related. A plan, target, prediction, or
schedule that reports no outcome is `unclear` about the outcome unless it
establishes a proper component of the proposition.

## Scope

`scope` records entity and population coverage as a diagnostic axis. It does not
rescue a non-supporting holistic relation.

- `match`: the passage concerns the same entity and fully covers the population
  or range asserted by the proposition.
- `evidence_narrower`: the passage covers a strict subset of the proposition's
  population or range.
- `evidence_broader`: the passage covers a strict superset while still including
  the complete proposition population.
- `mismatch`: it concerns a different, unlinked entity or incompatible range.
- `unclear`: scope cannot be resolved from the text.

Under this contract, evidence about one unlinked entity is not `supports` plus
`mismatch`; its holistic relation is `irrelevant`. Evidence establishing only a
strict subpopulation of a universal proposition is `partial` plus
`evidence_narrower`.

## Temporal status

- `compatible`: the passage is atemporal, addresses the requested time, or gives
  an explicit validity interval containing that time.
- `evidence_superseded`: an identified later authority replaces the passage for
  the requested time.
- `evidence_predates`: the passage reports an earlier state without establishing
  continuity to the requested time.
- `unclear`: temporal applicability cannot be resolved.

The r2 primary corpus uses explicit interval membership rather than relying on
an assessor to infer persistence from a prior observation. Ambiguity diagnostics
may intentionally have unresolved temporal applicability.

## Confidence and grounding

`confidence` is the assessor's self-report (`low`, `medium`, or `high`). It has no
gold target and is analyzed descriptively. One or two exact passage substrings
must ground every assessment. Confidence cannot turn incorrect semantics into an
admissible assessment.

## Structural validation and governance

The frozen G-EVID1 structural validator checks schema, bindings, exact quote
anchoring, truncation, and forbidden authority fields. It does not judge semantic
correctness. The frozen governor then maps a valid semantic assessment to
`use`, `investigate`, or `abstain`. `unsafe` remains a downstream scorer concept.

Structural rejection is retained as a separate scientific status even though
the operational governor safely maps it to `abstain`.

## Ambiguity diagnostics

Four separately identified diagnostics intentionally contain genuine linguistic
or contextual ambiguity. They are excluded from crisp primary semantic-accuracy
denominators and primary utility denominators. Their use-prohibition and expected
`investigate` disposition are scored separately. They cannot be used to relax or
reinterpret primary gold after results are observed.
