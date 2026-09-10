# v1500.7 Natural Association and Conversational Coherence Checkpoint

This checkpoint turns the v1500.2-v1500.5 association infrastructure into a lighter ordinary-conversation capability.

## Implemented behavior

- Natural family role references resolve through attributable graph edges before relationship reasoning.
- Directional relationship questions preserve the requested subject and object.
- Relationship questions are excluded from fact extraction and cannot contaminate memory.
- Newer durable single-value parent and partner roles supersede older conflicting edges across restart.
- Singular project and file pronoun follow-ups resolve only from one unambiguous user-authored subject.
- Assistant-authored claims and ambiguous references remain non-evidence.
- Active facts and association prompt blocks are selected by current-turn relevance instead of being attached to every casual provider request.

## Boundaries

This checkpoint does not contact a provider, infer authority, install or switch models, promote a release, or authorize source mutation. Durable memory still requires the existing explicit operator request and governed curation path. Unsupported or ambiguous associations continue to produce uncertainty rather than guesses.

## Verification

`python tools/v1500_7_natural_association_coherence_tests.py --json`

The focused suite covers role aliases, directionality, query contamination, durable correction precedence, relevant prompt selection, pronoun follow-ups, ambiguity, assistant-text exclusion, supersession lineage, content-free evidence, and authority neutrality.
