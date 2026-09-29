VERDICT: FINDINGS — BLOCKING 0, MUST-FIX 2, NOTE 8

I could not write REPORT.md. The harness refused the write ("Subagents should return findings as text, not write report files"), so there is no REPORT.md and no file sha256 to give. The full report is below, exactly as it was to be written. Save it to `...\scratchpad\corpus_review_r1\reviewer_B\REPORT.md` and hash that file if you need the digest.

Nothing in the repository was modified. Only read-only git was used, plus `git archive -o` into my scratch folder. There was no network, model or provider contact, and `~/.config` was never read.

---

# G-ROUTE4 external corpus review, round 1: Reviewer B report (protocol and provenance)

Date: 2026-09-29. Reviewer B, working alone. I did not look for, open or wait for anything from Reviewer A.

## 1. What was reviewed

- **Brief:** `experiments/G-ROUTE4-candidate/corpus_review/round1/REVIEWER_B_BRIEF.md`. Its LF-normalized sha256 is `b2760b0c709b52285a6fe25e6ca0b03cb6fbdfdb0a6721049f540ffacf3b5338`, as required.
- **Repository:** `C:\Users\marcu\Eidolon-g4adj`, branch `g-route4/adjudication`.
- **HEAD reviewed:** `97afe8a93def2c1eb572e38f567f68ab5cb53b4b` ("G-ROUTE4 step 3.7: external corpus review round 1 package"). Its parent `9908577` is the manifest's `package_built_at_parent_commit`. The worktree was clean apart from an ignored `__pycache__`.
- **Export:** HEAD was exported with `git -c core.autocrlf=false archive` into my scratch folder. Every check below ran on that copy. Python ran as `python -B` with the socket-blocking guard on `PYTHONPATH`.
- **REVIEW_MANIFEST.json digests: all match.**
  - File digests: both package files, all six reports, both briefs and `SEAL_MANIFEST.json`.
  - Content digests, recomputed from the files: the final A′ and B′ model-facing and gold sets, both reserve sets, the sealed and amended O2 configurations, `check_corpus.py` at `dd8193b` (`b3f6500b…`) and the frozen G-ROUTE3 detector (`177aa18a…`).
  - Git objects: the seal, tag object, audit-sample commit and blueprint commit ids.

## 2. Coverage

**Verified, and how:**

| Area | Method |
|---|---|
| Git provenance | Read-only `git` only: `rev-parse`, `for-each-ref`, `reflog`, `log`, `show`, `diff`, `cat-file`, `rev-list --children`, `status`, and `archive -o` into scratch. Checked the seal parentage, tag object, branch positions and reflogs, and every commit on the adjudication branch with timestamps. `git diff --name-status 50e6b46 HEAD` shows 1,596 files added and **none modified or deleted**. |
| Frozen files | Every `SEAL_MANIFEST.json` digest was recomputed: 15 file digests, 8 canonical digests, 6 blueprint files, the blueprint freeze manifest, the design, the obligations and 8 validator/rendering pins. All match. G-ROUTE1, G-ROUTE3 and `tools/` are unchanged from the G-ROUTE3 close commit `06af676` to HEAD. |
| O1 | Wrote my own derivation of the sample from the frozen formula over the blueprint at `1156d06` (B′ main cells, which I confirmed equal the sealed `corpus_b.json` ids). It matches the 38 committed ids and the sample digest `166f1f44…`. Also ran the frozen `audit_sample.py --self-test`, which gives `75af7d1a…`. |
| O2 configuration | Recomputed the sealed configuration digest (`1658b9a2…`) and the template digest (`8dd007c3…`). Ran `o2_amendment.py` in scratch (verify mode), which re-derives `7691126e…` from the sealed configuration. |
| Rendering | Checked all 770 model-facing fixtures (sealed and final). For each, the adjudicator rendering equals `g_route3_contract.render_prompt`. |
| Four run journals | Checked the hash chain, sequence numbers and canonical encoding of every line. Tallied config digests per record, invocation ordinals per slot, result kinds, HTTP statuses, stop reasons, response models, raw-file set equality, and raw-body and meta digests. |
| Request contents | I rebuilt every request body from the model-facing fixture and the amended body template. All **785** intents match the journal's `request_sha256`, which shows the sessions carried no gold. |
| Answers, scores and decisions | Rebuilt from the journal and raw bodies by my own code: binding invocation, binding-text digest and the journal-prefix digest in each answers file. **Re-scored all 765 bound slots** with the frozen `validate_operational` and `validate_fixture_output` against sealed or fixed gold, and re-derived every decision. **0 differences.** |
| Commit order | For each run and phase, checked answers commit, then scores commit (whose `answers_commit` field matches), then decisions, then operator decisions, then fixes, then the fix run. |
| Operator decisions | All four records: coverage of exactly the escalated set, options used, reasons and defects, and verdict arrays. I also ran my own diagnostic re-validation of every escalated answer with a leading and trailing code fence stripped. This is diagnostic only; recorded verdicts are untouched. It checks whether each "code fence only" reason is true. |
| Fixes | Re-ran `build_fixes.py` and `build_fixes_amain.py` in scratch: all 8 output files are byte-identical to the committed ones. Re-ran `check_fixes.py` and `check_fixes_amain.py`: both `FIX_CHECK_REPORT.json` files are byte-identical, with 0 problems. |
| Independence | Re-ran `build_independence_report.py` in scratch with git redirected read-only to the repository and the pinned local `cl100k_base` cache (digest `223921b7…` verified). The output is **byte-identical except `generated_at_parent_commit`**, as expected. Read the exempted checker rule (`research_allowed_bodies`) and the O3 code in `check_corpus.py`. |
| Closures and analysis | Re-ran `build_a_closure.py` and `build_contamination_analysis.py`: both outputs are byte-identical to the committed files. `B_MAIN_CLOSURE.json` has no committed builder, so I verified its numbers independently: tokens, slots, disagreements, causes, per-cell counts, totals, subsets, flags, audit-sample section and journal digests. |
| Final corpus | Independently checked that the 385 package fixtures equal the sealed main corpus with exactly the 20 recorded fixes overlaid. 20 model-facing records differ, 9 gold records differ (all within the 20), no others differ, and there are no replacements. |
| Latent-defect lists | Mechanically scanned the final main corpus and all 199 reserves for the four known defect patterns (SY1 `diagnosis` role, P6 `only`, weekend paraphrase, anonymity paraphrase). |

**Not checked (coverage is partial on these points):**

- Chat-side facts: that the operator started each batch and each resume in chat (D10); the operator's identity; the wording of the O2 amendment decision as given in chat. These are not in the repository.
- The provider documentation cited as O2 amendment evidence. I had no network access.
- That no provider contact happened outside the four journals, for example a probe before the amendment. I can only say that no other run directory exists, committed, untracked, ignored or deleted, and that each journal begins with its preflight.
- `estimated_cost_usd` (4.48) in `B_MAIN_CLOSURE.json`: no pricing source offline.
- Gold derivability and difficulty parity (Reviewer A's scope), and the adjudicators' thinking content.
- I did not run `test_g4_adjudicate.py` or any harness `run` command.

## 3. Findings

| Id | Class | Artifact / fixture | Evidence | Frozen remedy |
|---|---|---|---|---|
| B1 | MUST-FIX | Step-7 reading for the 9 fixed fixtures kept by the operator (B′: B4-RSRCH-R2-06, -R2-14, -R3-14, -R3-18; A′: A4-EXTR-R1-03, A4-RSRCH-R2-01, -R2-02, -R4-03, A4-SYNTH-R2-03); `fixes/LATENT_DEFECTS.md`; `runs/g4adj-bmain-fix1-…/FIX_ROUND_REPORT.json` | Design step 7: "'Failing again' means the re-adjudication does not end in 'keep', and the fixture is then replaced." All 9 were re-adjudicated, escalated, and then kept by operator "gold right → keep", so none was replaced. **The reading is defensible:** step 7 re-adjudicates "with the same procedure", and step 6 includes the operator's keep. **On the merits the keeps are sound:** my diagnostic finds every remaining disagreement is a fenced answer whose content passes the frozen validators. **But the reading was not fixed in advance for B′:** the B′ pre-declaration (`6818c50`) says only "if it fails, the frozen replacement procedure applies". The reading was settled after the fix-round results. When the operator decided (`f07b1a2`, 13:52), the record committed at 13:21 (`01e6ad3`) already called the four "not keep" / "did not end in keep" and said their only matching reserves carry the P6 defect. So the reading decided whether replacements were drawn and whether authoring would halt, and those stale labels still stand unannotated. (A′ did pre-declare "otherwise back to the operator before any replacement" at `8dc222f`, before its fix run.) | Before the freeze, record an explicit operator ruling on the step-7 reading. It should state that for B′ the reading was settled after the fix-round outcomes and the reserve defects were known, and cite the format-only evidence. Annotate the "did not end in keep" / "not keep" wording in an addendum. No re-adjudication is implied. |
| B2 | MUST-FIX | `adjudication/B_MAIN_CLOSURE.json` `disagreements.batch.by_cause` | It reports `format (code fence)`: 107 and `content`: 24. The records show 107 fenced answers, of which **16 also fail on content after the fence is stripped**, all in the 14 fixed fixtures. That leaves 91 format-only, 16 fence+content and 24 content-only. The table reads as a partition, so it understates content disagreements (40, not 24). `A_MAIN_CLOSURE.json` uses the correct split ("fence" 34, "fence+content" 8), so the two closures disagree in method. The B closure has no committed builder. | Correct the breakdown, or relabel it as the recorded reason, and state the fence+content count, in a disclosure update. No change to verdicts. |
| B3 | NOTE | A′ run `g4adj-amain-20260929T180225Z`, A4-PLAN-R1-03 slot 3 | Invocation 1 returned HTTP 400, "credit balance is too low". That is a billing rejection with no model output. The amended configuration `7691126e` classifies any 400 as `request_rejected`: "the batch stops; not retried". The operator recorded a resolution and a reclassification to `no_answer` (journal seq 214–215), and the slot's single retry (invocation 2) bound. This fits O2's own no-answer definition ("a session error with no final message"); no final message was discarded. It was decided before any answer was sealed or scored, and it did not affect the outcome: slot 2 also disagreed, so the fixture went to the operator either way. It departs from the letter of the amended error classification, though, and `O2_AMENDMENT_2026-09-29.md` does not mention it. The resume also ran on a different harness commit (`f0c4410`, diff verified to add only the reclassification) than the recorded `run_start` (`160dea1`). The only record of that change is prose in the resolution. | Add a one-line addendum to the O2 amendment record noting the one operator reclassification and the harness commit of the resumed segment. |
| B4 | NOTE | `adjudication/O2_AMENDMENT_2026-09-29.md`, `adjudicator_config_amended.json` | The configuration every session used is frozen at `94c11dd`. That is after the seal, and after the audit sample was public, not "in the seal commit". O2's change rule is what covers it: a recorded operator decision, with re-adjudication of every fixture vacuous because no session had yet run (amendment 15:52:42Z, first contact 15:58:39Z). Two settings were not forced by the provider: effort `high` rather than the default, and 32,000 output tokens. They were chosen before any contact, so they cannot depend on outcomes. | None. Recorded for the O2 verdict. |
| B5 | NOTE | A4-PLAN-R3-04 (A′ main) | All three adjudicators returned `stop_reason: refusal`, with `stop_details.category` "cyber" and empty output. So there is **no independent adjudicator evidence of derivability** for this A′ fixture; the non-blind operator kept it on their own derivation (the reason is recorded). It is disclosed in `A_MAIN_CLOSURE.json`. It is not among the "Warnings and latent issues carried to the corpus review" in `CONTAMINATION_ANALYSIS.md`. | Carry it explicitly to the corpus review (derivability is Reviewer A's scope). Any change goes through design step 10. |
| B6 | NOTE | O1 git parentage | The blueprint commit `1156d06` has two children: the seal `50e6b46` and the authoring root `8d890b2`. O1 is met on `main` because `main` was fast-forwarded to the seal (reflog 08:39 EDT; tag message). `8d890b2` is disclosed in `SEAL_NOTES.md` and in the tag. | None. |
| B7 | NOTE | `INDEPENDENCE_REPORT.json` tool, and the step 8 / blueprint §5 final re-check | The report uses `check_corpus.py` at `dd8193b`, the pinned authoring-stage tool. It imports the frozen G-ROUTE3 detector byte-identical, and it ran before the seal and at both fix re-checks. That is the right tool for this stage: the forked `g_route4_independence` does not exist until implementation, and the report says so. The "nothing in the tool is changed" wording is slightly loose: the builder replaces `research_allowed_bodies` at run time. I confirmed that function is used only by the authoring-paraphrase conformance check, and that the exemption covers exactly the 12 declared source texts, so it is as narrow as claimed. | Make it a freeze condition that the step-8 final re-check reproduces this report's values: the forked module (with N9) on the same final pool. |
| B8 | NOTE | Step-13 records | `B_MAIN_CLOSURE.json` per-cell counts are batch-only. The B′ fix round's per-cell slots and disagreements are not in any per-cell table, including `A_MAIN_CLOSURE.json` `step_13_records_all_cells.b_prime`. They are RSRCH-R2 6/4, RSRCH-R3 12/7, and RSRCH-R1, SYNTH-R1/R2/R3 2/0 each. The A′ table does carry fix-round columns. `audit_sample.cells_with_any_disagreement` means cells where a *sampled* fixture disagreed; the per-cell tables cover N4's "any disagreement within a sampled cell". | Add the B′ fix-round per-cell counts to the records bound in the freeze. |
| B9 | NOTE | 9 of the 20 fixes | Every fix was decided as "input ambiguous → fix input". In 9 of them the gold also changed: 8 SY1 role relabels, and the A4-EXTR-R1-03 key rename `venue`→`town`. The change is necessary and recorded in `FIX_RECORD.json` and the residual limitations, but the decision label alone understates it. | None beyond keeping the disclosure. |
| B10 | NOTE | D10 batch authorizations | The repository records do not include the operator's in-chat start of each batch or of the A′ resume, so I could not verify D10 from the records. | Consider binding each batch-start instruction (or its digest) in the run records. |

## 4. Verdicts per work item

**1. O1: PASS.**
- Exactly one commit on `main` has the blueprint as parent, the seal `50e6b46`; the disclosed authoring root is the other child (B6).
- The seal tree `eeb93d53…` and the tag object `86ff773c…` match.
- The committed sample re-derives exactly.
- The sample commit `29f5a47` (05:47Z) precedes the first logged session (preflight 15:58:39Z).

**2. O2: PASS, with notes B3 and B4.**
- **The sealed configuration** `1658b9a2…` is in the seal and unchanged.
- **The amendment** to `7691126e…` meets O2's change rule. It is a recorded operator decision, made before any provider contact, so re-adjudicating "every fixture" was vacuous. It is derived deterministically, and it keeps the model, prompt template, rendering, blindness, tools and retry rules.
- **One digest throughout:** every intent, result, phase and reclassification record in all four journals carries `7691126e…`. Only preflight, stop and resolution records carry no digest.
- **Ordinals:** 785 invocations over 784 slots. Exactly one slot has a second invocation, and no earlier final message went unused.
- **Binding rule:** the binding answer is the first final message, and it re-derives exactly.
- **Parse failures** count as disagreements (all fenced answers are recorded as `malformed_json`).
- **Refusals** bound as answers and scored as disagreements: the three on A4-PLAN-R3-04.
- **Provider rejection:** the one billing rejection was handled by a recorded operator reclassification into the frozen single retry (B3).
- **Response model:** every response names `claude-opus-5-5`, and no fallback was detected.

**Adjudication under `7691126e…` satisfies O2.**

**3. Adjudication procedure: PASS, with B1 to resolve.**
- **A′** had the full three-adjudicator treatment. **B′** had the first adjudicator, then two more on disagreement. All 38 sampled fixtures got adjudicators 2 and 3.
- **Audit-sample consequence:** none of the four sampled first-agreed fixtures that were escalated was fixed or replaced, so the pre-registered full-cell consequence was correctly not triggered.
- **Commit order:** answers were committed before scoring in every run and phase.
- **Operator decisions:** each covers exactly the escalated set, uses only "gold right → keep" and "input ambiguous → fix input", and has a reason or named defect. I checked each "code fence only" reason against the records and all are true.
- **Fixes and closures:**
  - 20 fixtures, each fixed once.
  - Each was re-checked (0 problems, reproduced) and re-adjudicated from scratch by the same procedure.
  - There were no replacements.
  - Both closures' counts reproduce, apart from the B2 wording.

**4. Independence: PASS.**

| Obligation | What the report shows |
|---|---|
| O3 | The scope string and the code show every class compared pairwise, main and reserve, against all of G-ROUTE3, with 0 shared entities (697 G-ROUTE4 entities) and 0 shared identifiers. |
| O4 | Conversation is listed as "no signature". |
| O5 | Zero boilerplate trigrams in family templates and zero single-family boilerplate, per class. |
| O6 | Fields per class and value counts (1,777), 0 collisions. |
| N3 | Restated as about 22 fixtures at a pool of about 150. |
| N7 | Stated: a fixed text replaces the old one and boilerplate is recomputed. |
| N8 | Reported for all 20 cells. |

- The report reproduces byte-for-byte except its generation commit.
- The fix-text exemption covers exactly the 12 declared research source texts and only an authoring-conformance rule.
- The tool is appropriate for this stage (B7).

**5. Seal and frozen inputs: PASS.**
- Nothing sealed, blueprint, audit sample, validator or pinned tool changed after the seal: every post-seal change is an addition.
- G-ROUTE1, G-ROUTE3 and `tools/` are unchanged.
- `main` = `origin/main` = `50e6b46` and `g-route4/seal` = `origin/g-route4/seal` = `29f5a47`, with no later reflog moves.
- The package equals the seal plus exactly the 20 recorded fixes, and both reserve sets are unchanged.
- No G-ROUTE4 thresholds file exists yet; the independence bounds come from the pinned tools, which are unchanged.

**6. Reports and disclosures: FINDINGS (B1, B2), otherwise accurate.**
- **`CONTAMINATION_ANALYSIS.md`** checks out:
  - its numbers: 1,777 values, 515 action names, 476 lineages, 259 and 507 invocations, the subsets, the 38 and 25 keeps, the fix effects and ranges, and N8;
  - its claim that no class-level measure changed, which I checked against the report's sealed-versus-final delta;
  - its claim that no reserve was sent, which I checked against every journal.
- **Latent-defect lists:** they match my mechanical scan exactly: 4 main-corpus SY1 fixtures, 14 reserves plus the weekend reserve, and no omissions.
- **Other disclosures present:** the residual filter, operator non-blindness, the O2 amendment, adjudication exposure and the declared blind spots.
- **Missing or inaccurate:**
  - the explicit step-7 ruling, and the stale "did not end in keep" wording (B1);
  - the B′ cause split (B2);
  - A4-PLAN-R3-04 as a carried warning (B5);
  - the one reclassification in the O2 amendment record (B3).

VERDICT: FINDINGS — BLOCKING 0, MUST-FIX 2, NOTE 8

---

REPORT.md sha256: none. The file could not be written (the harness blocked the write).

What is in my scratch folder (`...\scratchpad\corpus_review_r1\reviewer_B\`):
- the HEAD export (`head/`) and my check scripts;
- copies of the committed reports next to the reproduced ones.

Something I wanted to delete but could not: a scratch temp directory, `tmp\`, holding extracted staging exports from my first independence-report run. It is still in the scratch folder. The removal was blocked because the command's path could not be resolved safely, so I left it for you to delete if you want.