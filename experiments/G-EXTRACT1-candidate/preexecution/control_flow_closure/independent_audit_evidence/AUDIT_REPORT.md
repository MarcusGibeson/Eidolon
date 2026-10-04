# G-EXTRACT1 Independent Implementation Closure Audit

Verdict: PASS / READY_FOR_EXECUTION_FREEZE_REVIEW_ONLY.

No P1/P2 implementation finding or new scientific ambiguity was found in the completed scope. This is a mechanical implementation audit, not cognitive, scientific, provider, or model qualification. No repository repair was performed.

## Identity and Authority

- Sole fresh independent read-only auditor; no delegation.
- Actual workspace: `C:\Users\marcu\Eidolon-g4adj`; branch `g-extract1/design`.
- Starting reference: `694742a7cc3723f2c562121d5fc666cc777992ca`.
- Implementation: `17af89c9c4f279d55d48aac46125c2844d3b4ad5`.
- Current/evidence HEAD: `10cc8a978237fa6a403c1bfd72184845200b192e`.
- Accepted science closure: `6c85b10930cefe410a1965c0924e4fd9f47eb4ef`.
- Accepted package: `81dc9d05f49e9c1310bb38676bfd7cf6a8620cf7`.
- Audited candidate SHA256: `4819d754192df7c49055a825353b9387d2cf51efe9652ef9f64bda8736be62c1`.
- Audited runner SHA256: `70824534f88a0c08b5f88afde354aba7d83e23ed78560108139a4b85d9a88ef5`.
- All eight source-module working hashes equal both implementation and current committed blobs. The complete source map is in `FINAL_AUDIT.json`.
- Current candidate remains candidate-only, unactivated, with neither phase authorized. This audit does not activate a freeze or grant execution permission.

## First Independent Reproduction

After safe imports and package construction, the first behavioral actions were direct real `Run.perform` attacks, not producer helper calls: KeyboardInterrupt, then SystemExit, followed by GeneratorExit and a custom BaseException.

Each transport observed the persisted journal START before raising. External catch immediately inspected event lists, scoped events, and integrity files. The original exception object and arguments propagated unchanged; the already-persisted incident was `SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT`, category INVALID, phase A, cell `small:R2`. No COMPLETE, FAILURE, or fabricated provider receipt was created. Next scheduled perform was rejected before counting transport and before a second START. Deleting the run object and reconstructing from disk rejected the same frozen omission. Raw records and each incident/journal remain in `first_*` and `independent_raw.json`.

Fresh producer control helpers additionally covered result-validation signals, all four signal types in phase B, and RuntimeError/ValueError/OSError governed unreceipted FAILURE behavior. The generic guard catches IntegrityError/Exception only (`tools/g_extract1_runner.py:85`); the single BaseException handler is specific to the post-START transport invocation/result-validation boundary (`tools/g_extract1_runner.py:362`).

## Executed Scope

- 5,758 recorded assertions: 5,757 PASS, one incorrect auditor accounting assertion retained and explained below. Zero product assertion failures. Counts include three repeated precontact assertions before the helper-parent setup error; no producer counts were accepted without fresh execution.
- First independent reproduction: 25 assertions. Independently authored integrated prompt/schedule/duplicate attacks, LR1 malformed sealed checkpoints, source inspection, bindings, full report reconstruction, selector-span verification, historical and old-authority checks also executed.
- Fresh helper counts: CF 102; LR1 137; LR2 143; LR3 42; I1 15; I2 38; I3 22; I4 10; I5 8; I6 83. All passed. Every other group count is in the JSON report and raw assertion log.
- Ordinary/malformed transport outcomes: None, list, scalars, non-plain object, empty/partial/hybrid mappings, malformed success/failure receipts, invalid UTF-8, and exceptions. STARTs closed by governed FAILURE, continuation blocked, valid success/timeout/error/missing outcomes replayed.
- LR1 own correctly sealed payloads `[]`, null, number, string, boolean, and `{}`; helper wrong field types/domains and wrong envelopes. CORRUPTED_CHECKPOINT persisted and blocked valid resume, perform, and restart continuation.
- LR3 real identity/config checks and isolated actual protected-byte mutations, plus the ten frozen PRE-event matrix paths and replay. PRE_CONTACT_BLOCKED yielded all six A_BLOCKED, no contact and no B eligibility. Contacted INVALID/INCOMPLETE cases did not become A_BLOCKED.
- I1-I6: unverified-resume locks; retained skip/retry/prompt/manifest errors after catch/restart; resealed duplicate replay; receipt binding/kind/event/category attacks; START lineage and checkpoint prefix/position/schedule/binding/missing marker/fabricated seal; mechanical authorization exercise only, B grant accepted without A grant for resumed B, wrong-phase/candidate grants rejected.
- Actual 480 synthetic A `perform` calls executed afresh in the integrated helper. A-before-B eligibility, zero/mixed qualifiers, failed-A B_NOT_ELIGIBLE, running/failed/incomplete B, and full completed all-pass/mixed/all-fail B states verified through actual engine/replay paths.
- All 50 protected artifacts matched the complete manifest bindings. Representative AUTHORING_CANDIDATES.json, validate_corpus.py, independent_contamination.py, and validate_finalization.py isolated mutations were rejected before/after synthetic contact, after catch and on restart. Originals were never modified.
- 480 A / maximum 240 B / 720 schedules; all 64 conditional B subsets; 720 historical wire-byte comparisons; all 108 E5 selector-only audits independently consumed using exact published spans; all 12 elapsed clarifications preserved.
- Exact/duplicate/truncation/numeric scorer cases, qualification/family/repeat gates, reserve coverage/pair/consumption/postcontact guards executed.
- Both producer full clean pilot trees: exactly 1,447 files each, every file compared, identical hashes, exact producer file map. Both full 720 journals replayed. Each tree's 720 START wires and 720 COMPLETE call/receipt/output/evaluation bindings verified: 2,880 per-call assertions across the pair, plus two all-closed assertions. Full final report objects and checkpoint state/seal/lineage independently rederived. Valid full resume retained INCOMPLETE.
- Candidate/source/package/science-closure/model-receipt/schedule/schema/event-contract/report hashes and role aliases verified exactly. No live model-identity validation was attempted.

## Preservation

50,129 repository files in the protected/corpus/G-ROUTE4/preexecution snapshot matched before/after bytes. Git status matched that snapshot. The seven untracked corpus artifacts individually matched their manifest pins and original bytes. Historical G-ROUTE4 closure and unsafe-stop diagnostic equaled current and starting committed blobs; G-ROUTE4 remains CLOSED FAILED.

All three superseded candidates remain preserved and unactivated:

- `14fb601c3a58777942ccd0361c2a303b5bfcf10d4c05536a32d265c0babe537f`
- `6e7295b3c79ee95930fee7231265e342905b7848d261ae716d1ef1546ca785ab`
- `687a9a50d9bbbe480f3e74e103f5b75c621a46a9ffdcc8e80dab65f6b2915a35`

Their file paths and candidate-only statuses are recorded in `FINAL_AUDIT.json`. No old evidence was edited, removed, staged, or committed.

## Auditor Infrastructure Notes

Two temp-harness issues were corrected without repository changes or product repair. First, the integrity helper required its temp parent to exist; FileNotFoundError occurred before its next test, and the partial report is retained as `REPORT.json`. Second, the auditor initially counted every untracked file rather than only corpus artifacts, including a preexisting untracked producer `MECHANICAL_EVIDENCE_READOUT.md`. The erroneous assertion remains FAIL in the raw log. The corrected corpus-only assertion passed; full byte preservation and unchanged Git status had already passed. Neither was a P1/P2 product finding, scientific ambiguity, or post-audit repository repair.

## Boundaries and Evidence

All Python runs used `python -B -X utf8` and a socket tripwire installed before harness imports. Zero socket attempts and provider/model calls. No provider adapter imported, no network, Ollama, real Phase A/B, actual authorization/freeze activation, accepted-science mutation, staging, commit, or delegation.

No required implementation scope remains untested. Intentional limits: synthetic identities are not installed-provider attestations; mechanical grants are test objects only; reused producer720 journals are not a newly executed live experiment. The actual480A path was executed fresh. No qualification claim is made.

Persistent evidence root: `C:\Users\marcu\AppData\Local\Temp\gextract1-independent-audit-20261004-closure-final`.

Primary report: `FINAL_AUDIT.json`; readable report: `AUDIT_REPORT.md`; raw assertions: `suite_assertions.jsonl` and `independent_raw.json`; scripts: `audit.py`, `continuation.py`, `final_proofs.py`. All synthetic run directories and the original byte snapshot remain under this same root. `EVIDENCE_MANIFEST.json` seals the final files for byte-identical parent preservation.
