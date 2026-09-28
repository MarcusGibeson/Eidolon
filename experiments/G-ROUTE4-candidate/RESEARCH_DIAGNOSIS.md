# G-ROUTE3 grounded-research mismatches: read-only diagnosis

Date: 2026-09-28. Input for the G-ROUTE4 design candidate.

**This diagnosis changes nothing in G-ROUTE3.** G-ROUTE3 is closed. No record is regraded, and every
frozen verdict stands. The diagnosis only informs how G-ROUTE4's research fixtures, prompt and reporting are
designed.

## Method

- **Scope:** all 41 G-ROUTE3 research records whose frozen semantic evaluation contains `research_judgment_mismatch`.
  - Phase A attempt 2: 27. Phase B attempt 1: 14.
  - 26 of the 41 are false-clean: operationally accepted, but semantically wrong.
- **Records:** rebuilt from the sealed journals with the frozen scorer functions (`rebuild_records`, `attach_semantics`).
  They were read directly from the data root, with no lifecycle command, no writes and no model contact.
- **Diffs:** computed on the normalized payload the grader actually used (for example, after a fence was removed),
  field by field against gold: each claim's status, citations and lineages, then the recommendation and the uncertainty codes.
- **Labels:** each case was classified by reading the model-facing fixture (claims, sources, decision rule), the gold
  rationale and the model output.
  - Every case has one **primary** cause (the most upstream substantive error) and any **secondary** causes.
  - The taxonomy is the operator's eight classes. "Other" is split into two named, concrete causes (T8a, T8b).
- **Limit:** the labels are one analyst's reading; there was no independent adjudication.
  - Every gold answer checked was consistent with the stated rules, so no case is labelled fixture-side (T6).
  - G-ROUTE4's independent gold adjudication is the proper test of that claim for fresh fixtures.

## Taxonomy

| Code | Class | Primary | Involved (primary or secondary) | False-clean (primary) | small / mid / large (primary) |
|---|---|---|---|---|---|
| T1 | claim status misjudged (ordered status rules misapplied; the source text was read correctly) | 7 | 7 | 1 | 5 / 2 / 0 |
| T2 | source content misread | 1 | 1 | 0 | 1 / 0 / 0 |
| T3 | source scope / lineage misread (which sources are about the claim; narrower scope; lineage counting) | 11 | 11 | 5 | 4 / 7 / 0 |
| T4 | temporal relation misread | 0 | 0 | 0 | 0 / 0 / 0 |
| T5 | contradiction / support direction confused | 4 | 4 | 4 | 0 / 2 / 2 |
| T6 | fixture / gold genuinely ambiguous | 0 | 0 | 0 | 0 / 0 / 0 |
| T7 | validator / prompt mismatch (output element shape the prompt does not specify) | 4 | 18 | 3 | 0 / 1 / 3 |
| T8a | other: uncertainty-code rule not applied or misapplied, with the claim judgments right | 13 | 32 | 12 | 1 / 7 / 5 |
| T8b | other: decision rule misapplied, with the claim judgments right | 1 | 1 | 1 | 0 / 1 / 0 |

## Findings

1. **The mismatches cluster tightly: three reasoning patterns and one format issue.** "Research is bad" is not
   the finding.
   - **Uncertainty-code bookkeeping (T8a): involved in 32 of 41, primary in 13.**
     - `single_lineage_support` differs from gold in 30 of 41 cases.
     - Its condition is "some claim with status supported is supported by exactly one lineage". It is a
       cross-claim aggregate: it holds whenever *any* supported claim, often the uncontroversial second claim,
       rests on one lineage.
     - Models omit it in that situation. They also list it for claims that are unresolved or contradicted,
       whose one lineage does not count.
     - This is model-side: the condition is stated exactly, and gold applies it consistently.
   - **About-ness and scope (T3): primary in 11.** Three forms:
     - a narrower-scope source reported as `conflicting_sources` instead of `scope_mismatch`;
     - a source about a different venue or version cited for the claim;
     - two sources of one lineage counted as two lineages in a lineage-count decision rule.
   - **Conflict and governing-source rules (T1 and T5): primary in 11.**
     - **small:** sides with the more official source instead of returning `unresolved` when sources
       disagree and nothing governs (3). It also treats a single-lineage direct affirmation as not supported (2).
     - **mid:** skips the governing clause of rule 2 (2). It also reports a source-versus-claim contradiction as
       `conflicting_sources` (2).
     - **large:** twice reads the governing source's denial as support: 12 tonnes for a 20-tonne claim, and
       55 USD for a 40 USD claim.
   - **Output element shape (T7): involved in 18, primary in 4.**
     - Citations were written as `{source_id, lineage}` objects or `lineage:S1` strings; uncertainty codes as
       `{code: ...}` objects (copying the shape of `allowed_uncertainty_codes`); claims keyed as a dict.
     - In the 4 primary cases the substance matches gold exactly.
     - The prompt names the keys of a claim object, but never states that citations, lineages and uncertainty
       codes are lists of strings, or that claims is a list.
2. **The tiers fail differently.**
   - **large** (10 cases) never misjudged a claim's status or which sources are about it (0 T1, 0 T3). Its
     failures are bookkeeping (5), element shape (3) and two governing-source direction errors.
   - **mid** (20) fails mainly on bookkeeping (7) and about-ness/scope (7).
   - **small** (11) makes genuine claim-level errors: status (5), about-ness (4) and one numeric misreading.
3. **The dangerous class is concentrated.** Of the 26 false-clean cases, 12 are T8a (bookkeeping).
   - These are well-formed answers, often with every claim judged correctly, that miss or add a cross-claim code.
   - The false-clean answers that misjudge claims (T1, T3, T5) are 10.
4. **No temporal misreading (T4) was found.** The one date-governed fixture failed because the governing clause
   was not applied or its direction was confused, not because dates were misread.
5. **Protocol-side issues are limited to output shape (T7).** No validator behaviour was found to reject a
   substantively correct answer except through element shape.

## Implications for G-ROUTE4 (proposals; the operator decides)

- **Keep the research validator unchanged.** Exact match on claims, recommendation and uncertainties stays.
  Nothing is loosened.
- **Consider a pre-registered prompt clarification of element types (T7):**
  - `claims` is a list;
  - `citations`, `lineages` and `uncertainties` are lists of strings (source ids, lineage names, codes).
  - This is a protocol change and conflicts with decision D7 ("unchanged prompt"). It needs the operator's
    decision before the freeze. It would remove 4 purely formal failures and one confound in 14 others; it
    does not touch any judgment.
- **Report research accuracy at two levels, descriptively.** Next to the unchanged gate, report:
  - claim-level agreement (status, citations, lineages);
  - uncertainty-code agreement.
  This way a table can say whether a tier's research failures are judgment or bookkeeping. These are
  reporting additions, not gates.
- **Author fresh fixtures that separate the three patterns:**
  - some with every supported claim on at least two lineages, so `single_lineage_support` does not hold;
  - scope-narrower and other-subject sources in separate fixtures;
  - conflict fixtures both with and without a governing rule.
  Each pattern's failure rate can then be read directly.
- **Independent gold adjudication (already in the draft)** tests this diagnosis's "no ambiguous gold" reading on
  the fresh fixtures.

## Cases

Judgments are `claim=status[citations]; unc=[codes]; rec=recommendation`. For the model, citations written as
objects or `lineage:S1` strings are shown by their source id, and codes written as objects by their code, so
the substance can be compared. The grader dropped those malformed elements (see T7).

| # | Fixture | Phase / tier / repeat | Pattern | FC | Primary (secondary) | Model judgment | Gold judgment | Why | Side | G-ROUTE4 prompt / validator |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | A-RESEARCH-R3-2 | A / mid / r2 | S6_narrower_scope | no | T3 (T8a, T7) | C1=unresolved[S1]; C2=supported[S2,S3]; unc=['conflicting_sources', 'single_lineage_support']; rec=hold_rollout | C1=unresolved[S1]; C2=supported[S2,S3]; unc=['scope_mismatch']; rec=hold_rollout | C1's only source covers admin accounts, narrower than all users; the model listed conflicting_sources instead of scope_mismatch, and added single_lineage_support although the one-lineage claim (C1) is unresolved, not supported. Claims were keyed as a dict. | model-side | unchanged |
| 2 | A-RESEARCH-R3-2 | A / large / r2 | S6_narrower_scope | yes | T8a | C1=unresolved[S1]; C2=supported[S2,S3]; unc=['scope_mismatch', 'single_lineage_support']; rec=hold_rollout | C1=unresolved[S1]; C2=supported[S2,S3]; unc=['scope_mismatch']; rec=hold_rollout | Claims and scope_mismatch are right; single_lineage_support was added for C1, which is unresolved, not supported. | model-side | unchanged |
| 3 | A-RESEARCH-R3-1 | A / large / r2 | S1_positive_lineage_count_rule | yes | T8a | C1=supported[S1,S2]; C2=supported[S1]; unc=[]; rec=schedule_patch | C1=supported[S1,S2]; C2=supported[S1]; unc=['single_lineage_support']; rec=schedule_patch | Claims are right; C2 is supported by the advisory alone, so single_lineage_support names a supported claim resting on exactly one lineage was required and omitted. | model-side | unchanged |
| 4 | A-RESEARCH-R3-1 | A / small / r2 | S1_positive_lineage_count_rule | no | T1 (T7, T8a) | C1=supported[S1,S2]; C2=unresolved[]; unc=['conflicting_sources', 'single_lineage_support']; rec=schedule_patch | C1=supported[S1,S2]; C2=supported[S1]; unc=['single_lineage_support']; rec=schedule_patch | S1 directly states the restart requirement, so C2 is supported; the model made it unresolved, apparently treating one lineage as insufficient for status. Citations were objects. | model-side | unchanged |
| 5 | A-RESEARCH-R3-1 | A / mid / r2 | S1_positive_lineage_count_rule | yes | T8a | C1=supported[S1,S2]; C2=supported[S1]; unc=[]; rec=schedule_patch | C1=supported[S1,S2]; C2=supported[S1]; unc=['single_lineage_support']; rec=schedule_patch | Claims are right; single_lineage_support (C2 on the advisory alone) was omitted. | model-side | unchanged |
| 6 | A-RESEARCH-R2-2 | A / small / r1 | S5_conflict_unresolved | no | T1 (T7, T8a) | C1=contradicted[S1]; C2=supported[S1]; unc=[]; rec=verify_first | C1=unresolved[S1,S2]; C2=supported[S1]; unc=['conflicting_sources', 'single_lineage_support']; rec=verify_first | S1 denies and S2 affirms C1 with no governing source, so rule 2 makes it unresolved; the model sided with the official guidelines (contradicted) and did not cite the disagreeing blog. Citations were objects. | model-side | unchanged |
| 7 | A-RESEARCH-R2-1 | A / mid / r1 | S4_same_lineage_repetition | yes | T8a | C1=supported[S1,S2,S3]; C2=supported[S4]; unc=[]; rec=adopt | C1=supported[S1,S2,S3]; C2=supported[S4]; unc=['single_lineage_support']; rec=adopt | Claims are right; C2 rests on the marketing lineage alone, so single_lineage_support was required and omitted. | model-side | unchanged |
| 8 | A-RESEARCH-R4-2 | A / mid / r1 | S7_conflict_settled_by_rule | yes | T8a | C1=contradicted[S1,S2]; C2=supported[S3]; unc=[]; rec=use_detour | C1=contradicted[S1,S2]; C2=supported[S3]; unc=['single_lineage_support']; rec=use_detour | Claims are right; C2 rests on the traffic notices alone, so single_lineage_support was required and omitted. | model-side | unchanged |
| 9 | A-RESEARCH-R4-2 | A / large / r1 | S7_conflict_settled_by_rule | yes | T5 (T8a) | C1=supported[S2]; C2=supported[S3]; unc=[]; rec=allow_heavy_route | C1=contradicted[S1,S2]; C2=supported[S3]; unc=['single_lineage_support']; rec=use_detour | The later 2034 update governs and reduces the rating to 12 tonnes, denying the 20-tonne claim; the model cited only that update and marked C1 supported, then recommended the heavy route. | model-side | unchanged |
| 10 | A-RESEARCH-R4-2 | A / small / r1 | S7_conflict_settled_by_rule | no | T8a (T7) | C1=contradicted[S1,S2]; C2=supported[S3]; unc=[]; rec=use_detour | C1=contradicted[S1,S2]; C2=supported[S3]; unc=['single_lineage_support']; rec=use_detour | Claim substance is right (citations as objects); single_lineage_support (C2) was omitted. | model-side | unchanged |
| 11 | A-RESEARCH-R4-1 | A / mid / r2 | S8_quantitative_contradiction | yes | T5 | C1=contradicted[S1,S2]; C2=supported[S3]; unc=['conflicting_sources', 'single_lineage_support']; rec=withhold_certification | C1=contradicted[S1,S2]; C2=supported[S3]; unc=['single_lineage_support']; rec=withhold_certification | Both sources agree on 100 kg and together contradict the 140 kg claim; the model added conflicting_sources, treating a source-versus-claim contradiction as sources disagreeing. | model-side | unchanged |
| 12 | A-RESEARCH-R4-1 | A / mid / r1 | S8_quantitative_contradiction | yes | T5 | C1=contradicted[S1,S2]; C2=supported[S3]; unc=['conflicting_sources', 'single_lineage_support']; rec=withhold_certification | C1=contradicted[S1,S2]; C2=supported[S3]; unc=['single_lineage_support']; rec=withhold_certification | As case 11 (other repeat). | model-side | unchanged |
| 13 | A-RESEARCH-R4-1 | A / large / r1 | S8_quantitative_contradiction | yes | T7 | C1=contradicted[S1,S2]; C2=supported[S3]; unc=['single_lineage_support']; rec=withhold_certification | C1=contradicted[S1,S2]; C2=supported[S3]; unc=['single_lineage_support']; rec=withhold_certification | Substance matches gold exactly; the uncertainty code was written as an object {code: ...}, copying the shape of allowed_uncertainty_codes. | protocol-side | validator unchanged; prompt would need a pre-registered statement of element types (strings, a list) |
| 14 | A-RESEARCH-R1-1 | A / large / r2 | S2_direct_contradiction | yes | T8a | C1=supported[S1,S3]; C2=contradicted[S2]; unc=['single_lineage_support']; rec=hold | C1=supported[S1,S3]; C2=contradicted[S2]; unc=[]; rec=hold | Claims are right; single_lineage_support was listed although the only one-lineage claim (C2) is contradicted, not supported. | model-side | unchanged |
| 15 | A-RESEARCH-R3-2 | A / small / r1 | S6_narrower_scope | no | T3 (T8a, T7) | C1=unresolved[S1]; C2=supported[S2]; unc=[]; rec=hold_rollout | C1=unresolved[S1]; C2=supported[S2,S3]; unc=['scope_mismatch']; rec=hold_rollout | S3 (admin guide: failed sign-ins are logged) is about C2 and was not cited; scope_mismatch for C1 was omitted. Citations were objects. | model-side | unchanged |
| 16 | A-RESEARCH-R3-2 | A / mid / r1 | S6_narrower_scope | yes | T3 (T8a) | C1=unresolved[S1]; C2=supported[S2,S3]; unc=['conflicting_sources', 'single_lineage_support']; rec=hold_rollout | C1=unresolved[S1]; C2=supported[S2,S3]; unc=['scope_mismatch']; rec=hold_rollout | As case 1 (other repeat): narrower-scope source reported as conflicting_sources; single_lineage_support added for an unresolved claim. | model-side | unchanged |
| 17 | A-RESEARCH-R2-1 | A / mid / r2 | S4_same_lineage_repetition | yes | T8a | C1=supported[S1,S2,S3]; C2=supported[S4]; unc=[]; rec=adopt | C1=supported[S1,S2,S3]; C2=supported[S4]; unc=['single_lineage_support']; rec=adopt | As case 7 (other repeat). | model-side | unchanged |
| 18 | A-RESEARCH-R3-1 | A / small / r1 | S1_positive_lineage_count_rule | no | T1 (T7, T8a) | C1=supported[S1,S2]; C2=unresolved[S1]; unc=[]; rec=schedule_patch | C1=supported[S1,S2]; C2=supported[S1]; unc=['single_lineage_support']; rec=schedule_patch | As case 4 (other repeat); citations were written as 'lineage:S1' strings. | model-side | unchanged |
| 19 | A-RESEARCH-R3-1 | A / mid / r1 | S1_positive_lineage_count_rule | yes | T8a | C1=supported[S1,S2]; C2=supported[S1]; unc=[]; rec=schedule_patch | C1=supported[S1,S2]; C2=supported[S1]; unc=['single_lineage_support']; rec=schedule_patch | As case 5 (other repeat). | model-side | unchanged |
| 20 | A-RESEARCH-R4-2 | A / mid / r2 | S7_conflict_settled_by_rule | no | T1 (T8a, T7) | C1=unresolved[S1,S2]; C2=supported[S3]; unc=['conflicting_sources']; rec=use_detour | C1=contradicted[S1,S2]; C2=supported[S3]; unc=['single_lineage_support']; rec=use_detour | The decision rule says the later-dated source governs, which makes C1 contradicted; the model left it unresolved (the governing clause of rule 2 not applied). Claims were keyed as a dict. | model-side | unchanged |
| 21 | A-RESEARCH-R4-2 | A / large / r2 | S7_conflict_settled_by_rule | yes | T8a | C1=contradicted[S1,S2]; C2=supported[S3]; unc=[]; rec=use_detour | C1=contradicted[S1,S2]; C2=supported[S3]; unc=['single_lineage_support']; rec=use_detour | As case 8 (other repeat). | model-side | unchanged |
| 22 | A-RESEARCH-R1-2 | A / mid / r2 | S3_other_subject_unaddressed | yes | T3 (T8a) | C1=supported[S1]; C2=unresolved[S2]; unc=['conflicting_sources', 'scope_mismatch']; rec=keep_looking | C1=supported[S1]; C2=unresolved[]; unc=['single_lineage_support', 'unaddressed_claim']; rec=keep_looking | S2 is about Birch Centre, a different venue, and is not about C2 (Willow Hall catering); the model cited it, so C2 was not reported as unaddressed. | model-side | unchanged |
| 23 | A-RESEARCH-R1-2 | A / small / r1 | S3_other_subject_unaddressed | no | T3 (T7) | C1=supported[S1]; C2=unresolved[S2]; unc=['single_lineage_support', 'unaddressed_claim']; rec=keep_looking | C1=supported[S1]; C2=unresolved[]; unc=['single_lineage_support', 'unaddressed_claim']; rec=keep_looking | As case 22: the other venue's source was cited for C2 (uncertainties right). Citations were objects. | model-side | unchanged |
| 24 | A-RESEARCH-R1-2 | A / mid / r1 | S3_other_subject_unaddressed | yes | T3 (T8a) | C1=supported[S1]; C2=unresolved[S2]; unc=['conflicting_sources', 'scope_mismatch']; rec=keep_looking | C1=supported[S1]; C2=unresolved[]; unc=['single_lineage_support', 'unaddressed_claim']; rec=keep_looking | As case 22 (other repeat). | model-side | unchanged |
| 25 | A-RESEARCH-R2-2 | A / mid / r2 | S5_conflict_unresolved | yes | T8a | C1=unresolved[S1,S2]; C2=supported[S1]; unc=['conflicting_sources', 'scope_mismatch']; rec=verify_first | C1=unresolved[S1,S2]; C2=supported[S1]; unc=['conflicting_sources', 'single_lineage_support']; rec=verify_first | Claims and conflicting_sources are right; scope_mismatch was added with no narrower-scope source, and single_lineage_support (C2) omitted. | model-side | unchanged |
| 26 | A-RESEARCH-R2-2 | A / large / r2 | S5_conflict_unresolved | yes | T7 | C1=unresolved[S1,S2]; C2=supported[S1]; unc=['conflicting_sources', 'single_lineage_support']; rec=verify_first | C1=unresolved[S1,S2]; C2=supported[S1]; unc=['conflicting_sources', 'single_lineage_support']; rec=verify_first | Substance matches gold exactly; both uncertainty codes were written as objects. | protocol-side | validator unchanged; prompt would need a pre-registered statement of element types (strings, a list) |
| 27 | A-RESEARCH-R2-2 | A / small / r2 | S5_conflict_unresolved | no | T1 (T7, T8a) | C1=contradicted[S1]; C2=supported[S1]; unc=[]; rec=verify_first | C1=unresolved[S1,S2]; C2=supported[S1]; unc=['conflicting_sources', 'single_lineage_support']; rec=verify_first | As case 6 (other repeat). | model-side | unchanged |
| 28 | B-RESEARCH-R2-2 | B / mid / r1 | S7_conflict_settled_by_rule | yes | T1 (T8a) | C1=unresolved[S1,S2]; C2=supported[S3]; unc=['conflicting_sources', 'single_lineage_support']; rec=ask_for_quote | C1=contradicted[S1,S2]; C2=supported[S3]; unc=['single_lineage_support']; rec=ask_for_quote | The decision rule makes the published price list govern, so C1 (40 USD) is contradicted by 55 USD; the model left it unresolved and added conflicting_sources. | model-side | unchanged |
| 29 | B-RESEARCH-R2-2 | B / large / r1 | S7_conflict_settled_by_rule | yes | T5 | C1=supported[S2]; C2=supported[S3]; unc=['single_lineage_support']; rec=book_workshop | C1=contradicted[S1,S2]; C2=supported[S3]; unc=['single_lineage_support']; rec=ask_for_quote | The governing price list says 55 USD; the model cited it as supporting the 40 USD claim and recommended booking. | model-side | unchanged |
| 30 | B-RESEARCH-R3-2 | B / large / r1 | S5_conflict_unresolved | yes | T7 | C1=supported[S1]; C2=unresolved[S2,S3]; unc=['conflicting_sources', 'single_lineage_support']; rec=deny_access | C1=supported[S1]; C2=unresolved[S2,S3]; unc=['conflicting_sources', 'single_lineage_support']; rec=deny_access | Substance matches gold exactly; both uncertainty codes were written as objects. | protocol-side | validator unchanged; prompt would need a pre-registered statement of element types (strings, a list) |
| 31 | B-RESEARCH-R3-2 | B / small / r1 | S5_conflict_unresolved | no | T1 (T7, T8a) | C1=supported[S1]; C2=contradicted[S2,S3]; unc=['conflicting_sources', 'unaddressed_claim']; rec=deny_access | C1=supported[S1]; C2=unresolved[S2,S3]; unc=['conflicting_sources', 'single_lineage_support']; rec=deny_access | S2 (complete) and S3 (outstanding) disagree with no governing source, so C2 is unresolved; the model chose contradicted. Citations were objects. | model-side | unchanged |
| 32 | B-RESEARCH-R3-2 | B / mid / r1 | S5_conflict_unresolved | yes | T8a | C1=supported[S1]; C2=unresolved[S2,S3]; unc=['conflicting_sources']; rec=deny_access | C1=supported[S1]; C2=unresolved[S2,S3]; unc=['conflicting_sources', 'single_lineage_support']; rec=deny_access | Claims and conflicting_sources are right; single_lineage_support (C1 on training records alone) omitted. | model-side | unchanged |
| 33 | B-RESEARCH-R3-1 | B / mid / r1 | S2_direct_contradiction | no | T7 | C1=supported[S1,S2]; C2=contradicted[S3]; unc=[]; rec=reject_vendor | C1=supported[S1,S2]; C2=contradicted[S3]; unc=[]; rec=reject_vendor | Substance matches gold exactly; claims were keyed as a dict instead of a list. | protocol-side | validator unchanged; prompt would need a pre-registered statement of element types (strings, a list) |
| 34 | B-RESEARCH-R4-2 | B / mid / r1 | S4_same_lineage_repetition | no | T3 (T8a, T7) | C1=supported[S1,S2]; C2=supported[S3,S4]; unc=[]; rec=energize_panel | C1=supported[S1,S2]; C2=supported[S3,S4]; unc=['single_lineage_support']; rec=keep_isolated | C1's two sources share one lineage, so the two-lineage decision rule is not met; the model recommended energizing (and omitted single_lineage_support). Claims were keyed as a dict. | model-side | unchanged |
| 35 | B-RESEARCH-R4-2 | B / small / r1 | S4_same_lineage_repetition | no | T3 (T8a, T7) | C1=supported[S1,S2]; C2=supported[S3,S4]; unc=[]; rec=energize_panel | C1=supported[S1,S2]; C2=supported[S3,S4]; unc=['single_lineage_support']; rec=keep_isolated | As case 34; citations were written as 'lineage:S1' strings. | model-side | unchanged |
| 36 | B-RESEARCH-R4-1 | B / mid / r1 | S3_other_subject_unaddressed | yes | T3 (T8a) | C1=supported[S1,S2]; C2=unresolved[S3]; unc=['conflicting_sources', 'scope_mismatch']; rec=not_eligible | C1=supported[S1,S2]; C2=unresolved[]; unc=['unaddressed_claim']; rec=not_eligible | S3 is about firmware 4.0, not 4.1; the model cited it for C2, so C2 was not reported as unaddressed. | model-side | unchanged |
| 37 | B-RESEARCH-R2-1 | B / mid / r1 | S6_narrower_scope | yes | T3 (T8a) | C1=unresolved[S1]; C2=supported[S2,S3]; unc=['conflicting_sources', 'single_lineage_support']; rec=request_details | C1=unresolved[S1]; C2=supported[S2,S3]; unc=['scope_mismatch']; rec=request_details | As case 1 on a fresh fixture: the Saturdays-only source is narrower than Saturdays and Sundays; reported as conflicting_sources, plus single_lineage_support for an unresolved claim. | model-side | unchanged |
| 38 | B-RESEARCH-R2-1 | B / large / r1 | S6_narrower_scope | yes | T8a | C1=unresolved[S1]; C2=supported[S2,S3]; unc=['scope_mismatch', 'single_lineage_support']; rec=request_details | C1=unresolved[S1]; C2=supported[S2,S3]; unc=['scope_mismatch']; rec=request_details | Claims and scope_mismatch are right; single_lineage_support was added for C1, which is unresolved. | model-side | unchanged |
| 39 | B-RESEARCH-R2-1 | B / small / r1 | S6_narrower_scope | no | T3 (T8a, T7) | C1=unresolved[S1,S2]; C2=supported[S2,S3]; unc=[]; rec=request_details | C1=unresolved[S1]; C2=supported[S2,S3]; unc=['scope_mismatch']; rec=request_details | S2 (insurance) is not about C1 (weekend service) but was cited for it; scope_mismatch omitted. Citations were objects. | model-side | unchanged |
| 40 | B-RESEARCH-R1-2 | B / small / r1 | S8_quantitative_contradiction | no | T2 (T8a, T7) | C1=contradicted[S1]; C2=unresolved[S2]; unc=['conflicting_sources', 'scope_mismatch', 'single_lineage_support', 'unaddressed_claim']; rec=look_elsewhere | C1=contradicted[S1]; C2=contradicted[S2]; unc=[]; rec=look_elsewhere | 65 USD per evening contradicts 'under 50 USD'; the model made C2 unresolved and listed all four uncertainty codes. Citations were objects. | model-side | unchanged |
| 41 | B-RESEARCH-R1-1 | B / mid / r1 | S1_positive_lineage_count_rule | yes | T8b | C1=supported[S1,S2]; C2=supported[S1,S3]; unc=[]; rec=skip | C1=supported[S1,S2]; C2=supported[S1,S3]; unc=[]; rec=buy | Both claims are supported by two lineages, so the rule gives 'buy'; the model recommended 'skip'. | model-side | unchanged |

## Source text shown to the model, per fixture

### A-RESEARCH-R1-1

- Decision rule: Recommend 'adopt' only if every claim is supported; otherwise 'hold'.
- Claim C1: Quillnote queues edits made offline and syncs them later.
- Claim C2: Quillnote offers a free plan.
- Source S1 (lineage `quillnote-help-center`): Edits made without a connection are queued and synced when you reconnect.
- Source S2 (lineage `quillnote-pricing-page`): Plans: Solo 4 USD per month and Team 9 USD per user per month. There is no free plan.
- Source S3 (lineage `gadget-review-weekly`): Our testers confirmed that Quillnote's offline edits synced after reconnecting.
- Gold rationale: C1 has two lineages; the pricing page directly denies a free plan, so the rule yields hold.

### A-RESEARCH-R1-2

- Decision rule: Recommend 'book' only if every claim is supported; otherwise 'keep_looking'.
- Claim C1: Willow Hall has step-free access.
- Claim C2: Willow Hall allows outside catering.
- Source S1 (lineage `willow-hall-website`): The main entrance and the hall are step-free, with a ramp from the car park.
- Source S2 (lineage `birch-centre-website`): Birch Centre permits outside caterers once a form is signed.
- Gold rationale: S2 is about a different venue and is not about C2; C2 is unaddressed.

### A-RESEARCH-R2-1

- Decision rule: Recommend 'adopt' only if every claim is supported; otherwise 'hold'.
- Claim C1: Tallybook imports statements from Northbank.
- Claim C2: Tallybook exports reports as CSV.
- Source S1 (lineage `tallybook-marketing`): Tallybook connects to Northbank and imports statements daily.
- Source S2 (lineage `tallybook-marketing`): Press release: the new Northbank connector imports statements automatically.
- Source S3 (lineage `northbank-partner-directory`): Listed integration partner: Tallybook, statement import.
- Source S4 (lineage `tallybook-marketing`): Every report can be downloaded as CSV or PDF.
- Gold rationale: S1 and S2 share a lineage; C1 still has two lineages via S3; C2 rests on one lineage.

### A-RESEARCH-R2-2

- Decision rule: Recommend 'apply' only if every claim is supported; otherwise 'verify_first'.
- Claim C1: The Harbor Arts Fund accepts applications from unregistered community groups.
- Claim C2: The Harbor Arts Fund deadline is 2034-10-01.
- Source S1 (lineage `harbor-arts-fund-guidelines`): Applicants must be registered charities. Applications close on 2034-10-01.
- Source S2 (lineage `neighborhood-news-blog`): Good news: unregistered community groups can now apply to the Harbor Arts Fund.
- Gold rationale: S1 denies and S2 affirms C1 and the decision_rule names no governing source, so rule 2 makes it unresolved.

### A-RESEARCH-R3-1

- Decision rule: Recommend 'schedule_patch' only if C1 is supported by at least two lineages; otherwise 'investigate'.
- Claim C1: Gatewire release 7.2 fixes the session fixation flaw GW-2034-11.
- Claim C2: Installing Gatewire 7.2 requires a service restart.
- Source S1 (lineage `gatewire-security-advisory`): Release 7.2 resolves session fixation issue GW-2034-11. A service restart is required after installation.
- Source S2 (lineage `national-vulnerability-register`): GW-2034-11 (session fixation) is fixed in Gatewire 7.2.
- Gold rationale: C1 has two lineages so the rule is met; C2 rests on the advisory alone.

### A-RESEARCH-R3-2

- Decision rule: Recommend 'enable_vendor_sso' only if every claim is supported; otherwise 'hold_rollout'.
- Claim C1: Portico enforces multi-factor authentication for all users.
- Claim C2: Portico records failed sign-in attempts.
- Source S1 (lineage `portico-admin-guide`): Multi-factor authentication is enforced for administrator accounts.
- Source S2 (lineage `security-review-group`): Portico writes failed sign-in attempts to its audit log.
- Source S3 (lineage `portico-admin-guide`): Failed sign-ins are logged together with the source address.
- Gold rationale: S1 covers administrator accounts only, narrower than all users.

### A-RESEARCH-R4-1

- Decision rule: Recommend 'certify_harness' only if every claim is supported; otherwise 'withhold_certification'.
- Claim C1: The Apex fall-arrest harness is rated for users up to 140 kg.
- Claim C2: The Apex harness passed its drop test.
- Source S1 (lineage `apex-spec-sheet`): Maximum user weight: 100 kg.
- Source S2 (lineage `apex-user-manual`): Do not exceed a user weight of 100 kg.
- Source S3 (lineage `test-house-report`): Apex harness: drop test passed.
- Gold rationale: A 100 kg maximum contradicts a 140 kg rating.

### A-RESEARCH-R4-2

- Decision rule: When dated sources disagree about the same claim, the later-dated source governs and both are cited. Recommend 'allow_heavy_route' only if C1 is supported; otherwise 'use_detour'.
- Claim C1: Bridge K-9 is rated for 20-tonne vehicles.
- Claim C2: A detour suitable for heavy vehicles is signposted.
- Source S1 (lineage `state-bridge-inventory`): 2031 inventory: Bridge K-9 load rating 20 tonnes.
- Source S2 (lineage `state-bridge-inventory`): 2034 inspection update: Bridge K-9 rating reduced to 12 tonnes.
- Source S3 (lineage `county-traffic-notices`): Heavy vehicles are signposted to the Mill Road detour.
- Gold rationale: The 2034 update governs under the stated rule and denies the 20-tonne rating.

### B-RESEARCH-R1-1

- Decision rule: Recommend 'buy' only if every claim is supported by at least two lineages; otherwise 'skip'.
- Claim C1: The Fernpack 30 weighs under 1 kg.
- Claim C2: The Fernpack 30 comes with a rain cover.
- Source S1 (lineage `fernpack-product-page`): Fernpack 30: weight 0.92 kg. A rain cover is stored in the base pocket.
- Source S2 (lineage `trail-gear-lab`): We weighed the Fernpack 30 at 0.94 kg.
- Source S3 (lineage `hiking-forum-reviews`): My Fernpack 30 arrived with the rain cover tucked into the bottom pocket.
- Gold rationale: Both claims are supported by two lineages, meeting the rule.

### B-RESEARCH-R1-2

- Decision rule: Recommend 'reserve' only if every claim is supported; otherwise 'look_elsewhere'.
- Claim C1: The Linden community room seats at least 40 people.
- Claim C2: The Linden community room costs under 50 USD per evening.
- Source S1 (lineage `linden-centre-rooms`): Linden community room: seated capacity 32.
- Source S2 (lineage `linden-centre-prices`): Linden community room hire: 65 USD per evening.
- Gold rationale: A capacity of 32 contradicts at least 40, and 65 USD contradicts under 50 USD.

### B-RESEARCH-R2-1

- Decision rule: Recommend 'sign_contract' only if every claim is supported; otherwise 'request_details'.
- Claim C1: Brightline Cleaning services the office on both Saturdays and Sundays.
- Claim C2: Brightline Cleaning carries liability insurance.
- Source S1 (lineage `brightline-service-sheet`): Office visits are available on Saturdays.
- Source S2 (lineage `brightline-service-sheet`): Fully insured: public liability cover of 2 million.
- Source S3 (lineage `chamber-of-commerce-register`): Brightline Cleaning: liability insurance certificate on file.
- Gold rationale: The only source about C1 covers Saturdays, narrower than Saturdays and Sundays.

### B-RESEARCH-R2-2

- Decision rule: When the published price list and any other source disagree about a price, the published price list governs and both are cited. Recommend 'book_workshop' only if every claim is supported; otherwise 'ask_for_quote'.
- Claim C1: The Riverside print workshop costs 40 USD per person.
- Claim C2: The Riverside print workshop fee includes inks, paper and screens.
- Source S1 (lineage `riverside-sales-email`): Our print workshop is 40 USD per person.
- Source S2 (lineage `riverside-price-list`): Print workshop: 55 USD per person.
- Source S3 (lineage `riverside-price-list`): The print workshop fee includes inks, paper and screens.
- Gold rationale: The price list governs under the stated rule and denies the 40 USD price.

### B-RESEARCH-R3-1

- Decision rule: Recommend 'approve_vendor' only if every claim is supported; otherwise 'reject_vendor'.
- Claim C1: Vaultline encrypts stored backups.
- Claim C2: Vaultline supports point-in-time restore.
- Source S1 (lineage `vaultline-docs`): All backups are encrypted at rest with AES-256.
- Source S2 (lineage `independent-audit-2034`): Auditors verified encryption at rest for Vaultline backup storage.
- Source S3 (lineage `vaultline-docs`): Point-in-time restore is not supported; restores use nightly snapshots.
- Gold rationale: The vendor directly denies point-in-time restore.

### B-RESEARCH-R3-2

- Decision rule: Recommend 'grant_access' only if every claim is supported; otherwise 'deny_access'.
- Claim C1: Contractor Mira Sol completed the data-handling course.
- Claim C2: Contractor Mira Sol's background check is complete.
- Source S1 (lineage `training-records`): Mira Sol completed the data-handling course on 2035-02-03.
- Source S2 (lineage `hr-screening-portal`): Background check for Mira Sol: complete.
- Source S3 (lineage `vendor-coordinator-email`): Mira Sol's background check is still outstanding.
- Gold rationale: S2 affirms and S3 denies C2 with no governing rule, so it is unresolved.

### B-RESEARCH-R4-1

- Decision rule: Recommend 'release_eligible' only if every claim is supported; otherwise 'not_eligible'.
- Claim C1: Lift controller firmware 4.1 passed the regression suite.
- Claim C2: Lift controller firmware 4.1 was signed by the release authority.
- Source S1 (lineage `qa-regression-reports`): Firmware 4.1: 212 of 212 regression tests passed.
- Source S2 (lineage `independent-test-lab`): Replicated regression run for firmware 4.1: all tests passed.
- Source S3 (lineage `release-signing-ledger`): Firmware 4.0 was signed by the release authority on 2035-02-11.
- Gold rationale: S3 is about version 4.0, not 4.1, so nothing is about C2.

### B-RESEARCH-R4-2

- Decision rule: Recommend 'energize_panel' only if every claim is supported by at least two lineages; otherwise 'keep_isolated'.
- Claim C1: Panel P-12 holds a current electrical safety certificate.
- Claim C2: Panel P-12 passed its insulation resistance test.
- Source S1 (lineage `manufacturer-bulletin`): Panel P-12 ships with a current safety certificate.
- Source S2 (lineage `manufacturer-bulletin`): Reissued bulletin: the Panel P-12 certificate is current.
- Source S3 (lineage `commissioning-log`): Panel P-12 insulation resistance test: pass.
- Source S4 (lineage `site-inspector-notes`): Insulation resistance on Panel P-12 measured within limits.
- Gold rationale: C1's two sources share one lineage, so the two-lineage rule is not met.

