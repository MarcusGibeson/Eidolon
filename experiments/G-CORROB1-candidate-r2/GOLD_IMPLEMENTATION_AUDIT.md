# G-CORROB1-R2 fresh gold verification at implementation boundary

**Scope:** semantic review performed separately from scorer implementation.
The scorer did not generate, infer, or revise these judgments. No model/provider
was contacted.

**Independence limitation:** the current Codex task lineage participated in the
R2 design work. This is therefore an implementation-independent semantic audit,
not the historically independent signoff required by the R2 preregistration.
A qualified reviewer outside that authoring lineage must still sign all 32 items
before execution freeze.

## Item review

| ID | Proposition/evidence audit | Relation / scope / temporal | Eligibility | Result |
|---|---|---|---|---|
| R01 | Complete twelve-of-twelve record entails every parcel scanned. | supports / match / compatible | use | agree |
| R02 | One explicit unscanned parcel falsifies every. | contradicts / match / compatible | abstain | agree |
| R03 | One registered orchard establishes some. | supports / match / compatible | use | agree |
| R04 | One of four does not establish every. | partial / evidence_narrower / compatible | investigate | agree |
| R05 | Rule exactly preserves the medical-kit exception. | supports / match / compatible | use | agree |
| R06 | Exclusive South and never North contradict North passage. | contradicts / match / compatible | abstain | agree |
| R07 | Permission during staffed hours matches exactly. | supports / match / compatible | use | agree |
| R08 | Express denial while unstaffed contradicts at any time. | contradicts / match / compatible | abstain | agree |
| R09 | Must wear entails required. | supports / match / compatible | use | agree |
| R10 | Must wear contradicts not required. | contradicts / match / compatible | abstain | agree |
| R11 | May submit entails permitted. | supports / match / compatible | use | agree |
| R12 | Optional and not required contradict required. | contradicts / match / compatible | abstain | agree |
| R13 | Registry directly maps Halcyon to H-204. | supports / match / compatible | use | agree |
| R14 | Registry maps Zephyr to Z-881, contradicting H-204. | contradicts / match / compatible | abstain | agree |
| R15 | Eastern turbine is directly T-9. | supports / match / compatible | use | agree |
| R16 | One known turbine and two blanks establish only a subset. | partial / evidence_narrower / compatible | investigate | agree |
| R17 | Requested date is inside the inclusive validity interval. | supports / match / compatible | use | agree |
| R18 | Explicit invalidity boundary contradicts validity on that date. | contradicts / match / compatible | abstain | agree |
| R19 | 18:30 lies inside the stated closure. | supports / match / compatible | use | agree |
| R20 | Reopening at 19:00 contradicts closure at 19:30. | contradicts / match / compatible | abstain | agree |
| R21 | Signed successful completion log establishes completion. | supports / match / compatible | use | agree |
| R22 | Final aborted-before-completion record contradicts completion. | contradicts / match / compatible | abstain | agree |
| R23 | Final signed PASS establishes passing. | supports / match / compatible | use | agree |
| R24 | Prediction without a performed test leaves the outcome unresolved. | unclear / match / compatible | investigate | agree |
| R25 | Glossary directly defines triangle as east. | supports / match / compatible | use | agree |
| R26 | East definition contradicts triangle means west. | contradicts / match / compatible | abstain | agree |
| R27 | Signed dated rota directly establishes the assignment. | supports / match / compatible | use | agree |
| R28 | Same-date menu is unrelated to desk assignment. | irrelevant / mismatch / compatible | abstain | agree |
| D01 | Pronoun referent is unresolved between cup and vase. | unclear / unclear / compatible | investigate diagnostic | agree |
| D02 | Holiday exception cannot be resolved from the passage. | unclear / match / unclear | investigate diagnostic | agree |
| D03 | Rounded display cannot establish an exact decimal. | unclear / match / compatible | investigate diagnostic | agree |
| D04 | Modifier scope over managers is syntactically unresolved. | unclear / unclear / compatible | investigate diagnostic | agree |

## Result

- 28/28 crisp primary tuples remain defensible under the holistic semantic contract.
- 4/4 genuine ambiguity items remain correctly isolated from crisp semantic-accuracy denominators.
- No quantifier, qualifier, conjunction, temporal, scope, or eligibility defect was found.
- No gold value changed in this implementation audit.
- Historically independent signoff: **PENDING**.
