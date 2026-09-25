# G-ROUTE3 R7 — journal/replay lifecycle architecture (design revision 3)

Status: **design-review candidate, revision 3.** Revision 1 (`80a10d9`) and revision 2 (`fd5c9f8`) were each
reviewed by two independent reviewers and found not clean. Round-1 findings are recorded in
`R7_DESIGN_REVIEW_ROUND1.md`, round-2 findings in `R7_DESIGN_REVIEW_ROUND2.md`.

Revision 3 applies operator ruling 10 (§21). The code protects against **accidents and misuse of supported
commands**. **Tampering is caught at attempt boundaries**, by committed copies of each journal, instead of by
per-call git evidence. That per-call mechanism was the largest single source of round-2 findings.

Nothing scientific changes: corpora, gold, validators, prompts, the qualification rule, routing, gates,
thresholds and denominators are all as before. Grading changes are handled separately (§22). No implementation
is wired in, no execution freeze is written, no provider is contacted, and no scientific run is launched.

**Review sequence.**
1. Design review of this revision.
2. If clean, implementation from this document.
3. Implementation review, including the certification crash campaign.
4. Only then is an R7 execution freeze offered for authorization.

---

## 1. Guarantees and threat model

One G-ROUTE3 phase attempt sends a fixed-seed schedule of provider calls: 288 for Phase A, 144 for Phase B.

| | Guarantee | Holds against |
|---|---|---|
| **G1** | **At most once.** No schedule position is sent to the provider twice within one attempt. | Accidents: crashes, kills, power loss, a full disk, sharing violations, antivirus, `git clean`/`stash`. Also misuse of any supported command. |
| **G2** | **Truthful history.** Anything unproven is recorded as uncertain and disclosed, never guessed. | The same |
| **G3** | **No best-of-N.** A completed attempt cannot be discarded. Closures and optional stopping are disclosed. | The same. Also tampering with any attempt whose boundary is committed (§13). |
| **G4** | **A way forward.** Every reachable state has a supported command that leads to completion or to a recorded closure. The only exceptions are declared: a persistent scorer defect (§6), an integrity failure of a protected attempt or of a ledger (§9), and a lost evidence ref (§13). Each needs an operator ruling. | Accidents and misuse |
| **G5** | **Determinism.** Replay is a pure function of the run's files. Derived entries re-derive to identical payloads. | — |

**Threat model (operator ruling 10).** The code guarantees G1–G5 against accidents and misuse of supported
commands. Deliberately editing, deleting or planting files is out of scope for the code **between** attempt
boundaries. At every boundary, the attempt's journal and its ledger entries are committed to git (§13).
The table freeze and Phase B verify every attempt's on-disk journal byte for byte against its committed copy.
So tampering with any attempt that has passed a boundary is detected.

A deliberate adversary with a fake model server, a second checkout, or the ability to rewrite git history
remains out of scope, as before.

**Declared residual.** Tampering inside an attempt that is still in progress is not prevented by the code.
Examples are deleting the last journal files to have a call re-sent, or editing a record before its terminal
boundary. This is a trust assumption about the operator, stated openly.

## 2. Invariants

- **J1 — authority.** Each run has one append-only **journal**. Each phase has one append-only **ledger**
  journal of attempts (§9). Every other file is a projection, a committed copy, or a non-authoritative log.
- **J2 — sealed chain.** Every entry is sealed with its canonical digest (§4.4) and names the previous
  entry's seal. The first journal entry names the ledger head that it claims (§9.2).
- **J3 — durable, non-overwriting publication.** Entries are published only by the §14 protocol: write a
  temporary file, flush it, rename it without replace and with write-through, then flush the directory.
- **J4 — pure replay.** `replay(run files) → (state, observations)` is a pure, total function of the run
  directory. It never writes and never reads git. Repairs are made only by `recover()`, and only by the
  holder of the G-ROUTE3 lease (§15).
- **J5 — facts only.** Entries hold facts. Nothing recomputable is stored.
- **J6 — always sealable.** Every value passes through `safe_value`. Raw model text is stored as base64 plus
  the sha256 of its text.
- **J7 — deterministic derivations.** Derived payloads (`scoring_started`, `scored`, `completed`) are pure
  functions of sealed inputs. Every re-derivation is compared by **payload**, only against sealed or
  committed data.
- **J8 — one command shape.** Every command runs: G-ROUTE3 lease → boundary check (§13) → replay → drift check
  → recover to a fixpoint → decide → one publication → re-replay … → boundary commit if a boundary was
  reached.
- **J9 — way forward.** G4. §19 checks it mechanically.
- **J10 — inert telemetry.** Activity, telemetry and `recovery.log` are never read by any decision.
- **J11 — boundary evidence.** Before the first `call_started` of an attempt, the **consumption boundary**
  must be committed to git: the ledger entry and `run_created`. After a terminal entry, the **terminal
  boundary** must be committed: the whole journal. No command returns success until its boundary commit has
  succeeded or been recorded as pending. Every later command first completes any pending boundary commit.
- **J12 — at most once.** A call is sent only after its `call_started` is durably published. The next entry
  number is unique and publication never overwrites, so no second `call_started` for the same position can
  exist. A started call whose outcome is not durably recorded closes the attempt. The call is never repeated.
- **J13 — no closure after scoring begins.** Once every position is recorded and executed, the only entries
  that may follow are `scoring_started`, `scored` and `completed`. From `collected` onward, dependency drift
  and scorer failures make commands **refuse**. They never close the attempt.
- **J14 — zero transport retries.** Exactly one HTTP request is made per call (§17).

## 3. Files

```
data/g_route3/                      (git-ignored: survives `git clean -fd` and `git stash -u`)
    .lease                          the G-ROUTE3 lease (§15), one for both phases
  phase_{a,b}/
    ledger/000001.json ...          the attempt ledger journal (§9)
    runs/<run_id>/journal/000001.json ...    run journal entries
    runs/<run_id>/journal/NNNNNN.torn        a torn entry renamed in place by recover()
    runs/<run_id>/journal/.tmp-*             temporary files (never entries)
    runs/<run_id>/score.json, receipt.json   projections (written with §14)
    recovery.log                             non-authoritative
refs/g-route3/evidence              git ref of boundary commits (§13): committed copies of ledgers and journals
```

Replay considers only files named `NNNNNN.json` or `NNNNNN.torn`. Anything else is reported and ignored.

## 4. Journal entries

### 4.1 Envelope

```json
{"entry": n, "kind": "…", "run_id": "…", "previous_entry_sha256": "…", "payload": {…}, "record_sha256": "…"}
```

For entry 1, `previous_entry_sha256` is the seal of the ledger head that `run_created` claims to follow.
An entry published after a `.torn` also carries `"acknowledges": {"entry": n, "sha256": "…"}` in the
envelope (sealed), so a derived entry's payload stays equal to its re-derivation. There is no timestamp in
any seal. Times appear only in `recovery.log` and the git commits.

### 4.2 Kinds

| Kind | Payload | May follow |
|---|---|---|
| `run_created` | Phase, attempt number, authorization digest, claimed ledger head; schedule, guarded and freeze digests; synthetic flag; fixed endpoint; model receipts; transport contract; for Phase B, the table digest, Phase A run id, and the evidence commit id bound into the table | Nothing: it is entry 1 |
| `call_started` | Position k, call id, request digest, guarded digest observed now | `run_created` (k = 1); a clean `call_recorded` for k−1 (a non-coding call); a clean `execution_recorded` for k−1 |
| `call_recorded` | Position k (must equal the preceding `call_started`); provider raw body (base64) and its sha256; raw output (base64) and the sha256 of its text; returned model; scalar metrics; `transport_failure` (empty unless the provider boundary raised) | `call_started` k |
| `execution_started` | Position k, candidate digest | `call_recorded` k of a coding call with no transport failure |
| `execution_recorded` | Position k, sandbox evidence, candidate error, `infrastructure_failure` | `execution_started` k |
| `scoring_started` | Digest of the fact prefix; for Phase B, seals of the disclosure inputs (the ledger head, and each earlier attempt's terminal entry) | Every position recorded and executed cleanly |
| `scored` | Score report: a pure function of the sealed inputs named in `scoring_started` (§4.3) | `scoring_started` |
| `completed` | Receipt: chain head seal, `scored` seal, `run_created` seal, freeze and guarded digests | `scored` |
| `closed` | A state (`incomplete`, `failed` or `cancelled`) and a reason from the closed list below, plus `calls_started`, `calls_recorded`, `executions_started`, the in-doubt position if any, the exception class and message if any, and the sha256 values of the temp and torn files it acknowledges | `run_created`, `call_started`, `call_recorded`, `execution_started`, `execution_recorded`. Never after `scoring_started` (J13) |

**Closed list of `closed` reasons:**
- `call_outcome_unknown`
- `transport_failure`
- `infrastructure_failure`
- `execution_interrupted`
- `durability_uncertain`
- `guarded_dependency_drift_refused` (this never closes; it is listed only so that it is disclosed)
- `abandoned_preflight_failed:<checks>`
- `operator_interrupt`
- `operator_cancelled`

**What ends collection.** Any failure field set, `call_outcome_unknown`, or `execution_interrupted` leads
the next decision to `closed`. A call is never retried.

### 4.3 Determinism

The inputs to `scored` are:
- the sealed fact entries of this run;
- the frozen corpora, gold and table, bound by the digests in `run_created`;
- for Phase B's attempt disclosure, the sealed ledger entries and the terminal entries of earlier attempts
  whose seals `scoring_started` names.

A re-derivation must reproduce the same payload. If it does not, the result is an integrity failure (§9.4).
It is never overwritten.

### 4.4 Canonical JSON

A seal is the sha256 of `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
allow_nan=False).encode("utf-8")`, where `value` has passed through `safe_value`. Integers of 10^30 or more
become strings. Floats use the shortest round-trip `repr`.

## 5. Replay: an ordered, total decision procedure

The run directory's entries are the `NNNNNN.json` and `NNNNNN.torn` files. Temporary and foreign files are
recorded as observations. An `n.json` whose bytes equal an existing `n.torn` is treated as that `.torn` alone
(a POSIX rename interrupted between link and unlink; recovery unlinks the `.json`). Rules apply **in order;
the first match wins**:

| # | Condition | State |
|---|---|---|
| R0 | No `journal/` directory, or it has no `.json` and no `.torn` entries (temporary or foreign files only) | `absent` (with observations) |
| R1 | Any `.json` entry fails to parse or seal, **other than the highest-numbered file** | `integrity_failure` |
| R1a | Any `.json` entry that parses and seals, **including the last**, fails a grammar or payload check. The checks: its number equals its file name; its run id is constant; its previous-seal link is correct (an acknowledging entry links to n−1, skipping the `.torn` at n); the kind order follows §4.2; positions and call ids match the schedule; `closed` never follows `scoring_started`; nothing continues after a failure field; the `completed` receipt matches the chain | `integrity_failure` |
| R1b | Numbers 1 … highest are not each occupied by exactly one `.json` or `.torn`. Or a `.torn` at n is not the highest entry and entry n+1 does not acknowledge it (envelope field `acknowledges` = {n, sha256 of the torn bytes}, previous seal = that of n−1). Or a `.torn` sits at entry 1 with any later entry | `integrity_failure` |
| R2 | The highest-numbered `.json` fails to parse or seal | `torn_tail(n, predicted)` |
| R3 | The highest-numbered entry is a `.torn` | `torn_pending(n, predicted)` |
| R4 | The last entry is `completed` | `completed` |
| R5 | The last entry is `closed` | `closed` |
| R6 | The last entry is `scored` | `scored` |
| R7 | The last entry is `scoring_started` | `scoring_interrupted` |
| R8 | The last entry is `execution_started` k | `execution_in_doubt(k)` |
| R9 | The last entry is `call_started` k | `in_doubt(k)` |
| R10 | The last entry carries a failure field | `faulted(k)` |
| R11 | The last entry is `call_recorded` k of a coding call | `awaiting_execution(k)` |
| R12 | Every position is recorded and executed cleanly | `collected` |
| R13 | The last entry is a clean record of k, where k is less than N | `collecting(k)` |
| R14 | The last entry is `run_created` | `created` |

**Predicting the kind of a torn entry** (used by R2 and R3). The prediction comes from the kind of the
previous entry and the fact prefix, **excluding `closed`**:

- after `call_started`, the next kind is `call_recorded`;
- after a coding `call_recorded`, it is `execution_started`;
- after `execution_started`, it is `execution_recorded`;
- after a clean record of k less than N, it is `call_started`;
- once every position is recorded and executed, it is `scoring_started`;
- after `scoring_started`, it is `scored`;
- after `scored`, it is `completed`;
- for entry 1, it is `run_created`.

`closed` is never predicted. A torn `closed` is handled by §6.

## 6. `recover()`: one publication per step, by the lease holder

**Drift comes first.** Before any recovery step that computes a derived entry or runs the sandbox, the
guarded digest is compared with the one in `run_created`. If it differs, the command refuses and names the
drifted paths.

| State | Recovery step |
|---|---|
| `torn_tail(n, k)` | Rename `n.json` to `n.torn` with no replace. On POSIX, if `n.torn` already exists with identical bytes, unlink `n.json` instead. Then re-replay. |
| `torn_pending(1, run_created)` | No call can have been made (no later entry exists). If no ledger entry names this run, it is an orphan (`--clear-orphan`, §9.4). Otherwise recover publishes `attempt_closed_at_ledger(durability_uncertain)` and commits it. The next attempt uses the ordinary sentence. |
| `torn_pending(n, call_started / call_recorded / execution_started / execution_recorded)` | Publish `closed(incomplete, durability_uncertain, torn=[n, sha256])` at n+1, chained to n−1 |
| `torn_pending(n, scoring_started / scored / completed)` | Drift check first. Re-derive the entry and publish it at n+1, chained to n−1, acknowledging n. If a committed copy of an entry with that payload's kind exists (§13), the payloads must be equal; a mismatch is an integrity failure. |
| `in_doubt(k)` | Publish `closed(incomplete, call_outcome_unknown, in_doubt=k)` |
| `execution_in_doubt(k)` | Publish `execution_recorded(k, infrastructure_failure=execution_interrupted)`. The attempt then closes. The sandbox is never re-run, and the provider output is kept. |
| `faulted(k)` | Publish `closed(incomplete, <failure reason>)` |
| `awaiting_execution(k)` | Publish `execution_started` k, run the sandbox once, and publish `execution_recorded` k |
| `scoring_interrupted` | Run the scorer in a subprocess with a timeout. On success, publish `scored`. **On failure, refuse** (J13): the scorer is provider-free and deterministic, so a persistent failure is a defect that needs a change record under an operator ruling, and the attempt stays open. |

Torn bytes are never parsed for decisions. A torn `closed` is predicted as whatever its position allows
(a provider kind), so it closes again as `durability_uncertain`; the `.torn` stays in place and in the
committed copy, so an auditor can still read its original reason.

**Temporary files.**
- A temporary file that is **byte-identical** to the entry published at its number is deleted.
- Any other temporary file is renamed to `.orphan-tmp-<n>-<token>`, and its sha256 is named in the next
  `closed` or recovery entry.
- No provider output is ever deleted.

## 7. Commands

Every command takes the G-ROUTE3 lease. It completes any pending boundary commit, replays, runs the drift check,
and recovers to a fixpoint, then acts:

| State after recovery | launch n | `--resume` n | `--abandon` n | `--declare-integrity-failure` n |
|---|---|---|---|---|
| no run, attempt n unconsumed | publish `run_created`, then the ledger entry, then the **consumption boundary** commit, then collect | refused | refused | refused |
| `absent`, attempt n consumed | refused | refused | refused | allowed (§9.4) |
| `created`, `collecting` | refused | collect | allowed only if its preflight fails (§9.3) | refused |
| `collected` / `scored` | refused | score and complete | refused | refused |
| `completed` | refused | re-project and re-commit only | refused | **refused** (§9.4) |
| `closed` | the next attempt is allowed | refused | refused | refused |
| `integrity_failure` | refused | refused | refused | allowed, unless the attempt is protected (§9.4) |
| a run folder without a ledger entry | refused | refused | refused | refused; `--clear-orphan` applies instead |

**Drift in `created` or `collecting`.** The command refuses until the guarded files are restored, and names
the changed paths and digests. It does not close. The calls already recorded were checked against the guard.

**Interrupts.** SIGINT, SIGTERM and CTRL_BREAK during a call are caught. The command publishes
`closed(incomplete, operator_interrupt, in_doubt=k)` if `call_started` k exists without a record. Otherwise
the next command classifies the state as usual.

**Run id and attempt number.** The run id is taken from the ledger entry of the attempt named in the
sentence. Attempt n must equal the number of consumed attempts plus 1 on launch. On `--resume` it must equal
the latest consumed attempt; `--resume` of an attempt that has a later attempt is refused.

**Sentences** (exact, full-match regular expressions; `<binding>` and `<table>` are 64 lowercase hex):
- `^Authorize G-ROUTE3 phase A execution ([0-9a-f]{64}) attempt ([1-9][0-9]*)$`
- `^Authorize G-ROUTE3 phase B execution ([0-9a-f]{64}) table ([0-9a-f]{64}) attempt ([1-9][0-9]*)$`
- the distinct forms of §9.4, which append ` after integrity failure of attempt ([1-9][0-9]*)` and require
  it to equal n−1.

**`--freeze-table`** works as follows:
- It requires the Phase A attempt named in its sentence to replay as `completed`, and its terminal boundary
  to be committed.
- It checks that every other Phase A attempt is closed or closed at ledger level, and that each one's
  on-disk journal equals its committed copy.
- It builds the table from the replayed `scored` entry. The table records the `run_created` seal, the
  `scored` seal, and the id of the evidence commit holding them.
- The audit record must read `READY` and names both seals. It is bound by the document's sha256, and the
  document must not be a frozen artifact.
- The table is published with §14, without replace, and then committed.
- A rerun that finds an identical table does nothing. A different table is refused.

## 8. One call

1. Guard check. Re-verify the lease token.
2. Publish `call_started` k (§14). A crash from here until step 4 completes gives `in_doubt(k)`, which closes
   the attempt.
3. Send exactly one request (J14).
4. Publish `call_recorded` k, with `transport_failure` if the provider boundary raised.
5. For a coding call:
   - publish `execution_started` k;
   - run the sandbox once;
   - publish `execution_recorded` k.

   A crash between `execution_started` and `execution_recorded` gives `execution_interrupted`. The attempt
   closes and the sandbox is not re-run.
6. If a failure field is set, publish `closed`.

No git operation happens inside the per-call loop.

## 9. Attempts: the ledger

### 9.1 Ledger entries

The ledger is a hash-chained journal per phase, under `data/`, with the same envelope, protocol, replay rules
R0–R3, torn and temporary handling, and grammar checks as a run journal. It has three kinds:

- **`attempt_consumed`:** attempt number, the verbatim sentence, authorization digest, run id, the run
  root, and the `run_created` seal.
- **`attempt_closed_at_ledger`:** attempt number, reason (`integrity_failure`, `journal_missing`, or
  `durability_uncertain` for a torn `run_created`, §6), and
  the evidence observed. Its counts come from the attempt's committed copy if one exists, otherwise from
  what can be read.
- **`ledger_torn_acknowledged`:** acknowledges a torn ledger tail. A torn `attempt_consumed` is followed by
  it together with a closure of that attempt at ledger level, as `durability_uncertain`. No call can have
  been made, because J11 requires the consumption boundary to be committed first.

**Recovery from a lost ledger.** If the ledger files are missing or shorter than their committed copy, the
recovery step restores the committed prefix byte-identically from the evidence ref, using §14. The committed
copy wins. A ledger that fails anywhere other than its tail is an integrity failure of the phase. That needs
an operator ruling.

### 9.2 Order at launch

The steps are:

1. Take the G-ROUTE3 lease.
2. Publish `run_created`. Its previous seal is the ledger head it claims.
3. Publish `attempt_consumed`, naming the `run_created` seal.
4. Make the **consumption boundary** commit (§13).
5. Collect.

**What an interruption leaves.**
- **Between 2 and 3:** an orphan with no calls. `--clear-orphan` handles it.
- **Between 3 and 4:** the attempt is consumed but uncommitted. No call is allowed yet. The next command
  commits it first.

### 9.3 Attempt policy

- **Launch.** Attempt n+1 may be launched only when every earlier attempt is `closed` or closed at ledger
  level. The first `completed` attempt is the result.
- **Abandon.** `--abandon` is allowed only when the command's own preflight fails with a **persistent**
  condition: the model receipts differ from the frozen bindings (for example after an Ollama update), or the
  freeze no longer verifies. An unreachable provider or a transient error is not a preflight failure;
  `--resume` handles that by closing through the normal paths. Guarded-dependency drift is not a preflight
  failure either, because it refuses until restored. The closure reason lists the failing checks, and is
  recorded automatically.
- **Optional stopping.** Killing the process or interrupting it during collection cannot be prevented
  mechanically. It is disclosed (§12).

### 9.4 Integrity failures, missing journals and protected attempts

**`--declare-integrity-failure n`** publishes `attempt_closed_at_ledger` and commits it, together with the
run folder's files as found (its terminal boundary). It leaves the folder in place. It is **refused** if
attempt n is protected:

- its committed terminal copy is `completed`; or
- the longest valid prefix of its on-disk journal (the entries before the first one that fails R1–R1b)
  reaches `collected` or beyond; or
- it is the Phase A attempt a frozen table names.

Such an integrity failure blocks the phase until an operator ruling. It is never a path to another attempt.
So a visible result cannot be discarded by damaging its files.

**After an allowed declaration**, the next attempt requires the distinct sentence:

- `Authorize G-ROUTE3 phase A execution <binding> attempt <n> after integrity failure of attempt <n-1>`
- `Authorize G-ROUTE3 phase B execution <binding> table <table> attempt <n> after integrity failure of attempt <n-1>`

The ordinary sentence is refused in that case, and the distinct sentence is refused otherwise. A
`journal_missing` closure uses the same sentences.

**`--clear-orphan`** accepts only a run folder with no `call_started` and no ledger entry. It commits an orphan
record and the folder's files first, then moves the folder aside to `runs/.orphan-<run_id>-<token>` with a
no-replace directory rename (`MoveFileExW` without replace; POSIX `renameat2(RENAME_NOREPLACE)`, or failing
that `mkdir` of the target followed by per-file no-replace moves). Orphans are disclosed.

## 10. Phase B preconditions

Phase B may contact the provider only when all of these hold:

1. The named Phase A attempt replays as `completed` at the fixed root, with no unacknowledged `.torn` file.
2. It is the only completed Phase A attempt. Every other Phase A attempt is closed or closed at ledger level.
3. Every Phase A attempt's on-disk journal and ledger entries equal their committed copies, byte for byte.
4. Its `run_created` attempt and authorization digest equal its ledger entry. The ledger entry names the
   `run_created` seal.
5. It is not synthetic, it ran under this freeze, and its guarded digest (in `run_created` and in every
   `call_started`) equals today's. Its model receipts verify, and its endpoint is the fixed one.
6. The provider evidence of every call is consistent: body digest, model, output, and request digest against
   the schedule.
7. Cells re-derived from its facts equal the `scored` cells and the table's cells.
8. **Table checks carried over from R6:**
   - the table's digest recomputes;
   - the routing lookup is exactly what the cells imply;
   - the table is derived from Corpus A alone (`corpus_b_consulted` false);
   - its corpus, gold and threshold digests match;
   - it is bound to this freeze;
   - its audit reads `READY`, is bound to a document whose sha256 still matches, names the `run_created`
     and `scored` seals, and is not a frozen artifact.
9. The table names the evidence commit that holds this attempt's terminal copy. The table's attempt
   disclosure equals the disclosure computed now (§12).
10. The Phase B sentence names the freeze, the table and attempt n, and is consumed through §9.
11. The table file is inside Phase B's per-call guard, as in R6.

## 11. Durability summary

- **At most once (G1) needs no git.** It rests on `call_started` being durably published (§14: flushed
  temp, write-through no-replace rename, directory flush) before the request, and on the unique next entry
  number. A power loss that loses an unflushed rename can only lose an entry whose request was never sent.
- **Every journal and ledger entry is durable before the next step that depends on it.** Projections and
  `recovery.log` carry no authority, so losing them costs nothing; projections are rebuilt.
- **Boundary commits are durable before the command reports success.** Every git call runs with
  `-c core.fsync=all -c core.fsyncMethod=fsync` (git 2.36 or later; preflight checks the version), and the
  directory holding the loose ref is flushed after `update-ref`.
- **What is lost to an accident is recorded, never guessed:** an in-doubt call closes the attempt, a torn
  entry is kept in place, and an unmatched temp file is kept under a unique name.

## 12. Disclosure

The qualification table and the Phase B score disclose, for every attempt of the phase:

- attempt number, run id, outcome, and closure reason;
- `calls_started`, `calls_recorded`, `executions_started`, and the in-doubt position if any;
- whether the reason could have been caused by the operator (`operator_interrupt`, `abandoned…`,
  `call_outcome_unknown`);
- **partial results**:
  - for Phase A, cells re-derived from the attempt's recorded calls;
  - for Phase B, per-observation correctness of its recorded calls, and the routing decisions it could
    determine;
- for every seeded position recorded in more than one attempt, whether the raw-output sha256 values are
  identical;
- orphans cleared, declarations made, and the evidence commit id of each attempt's boundaries.

## 13. Boundary commits (git)

There are three kinds of boundary commit:

- **Consumption boundary:** after `attempt_consumed`, and before any `call_started`.
- **Terminal boundary:** after `completed` or `closed`, and after any ledger-level closure.
- **Table freeze.**

Each commit adds that attempt's ledger entries; at the consumption boundary, its `000001.json`
(`run_created`); and, at the terminal boundary, every file in its
`journal/` directory (entries, `.torn` files and `.orphan-tmp-*` files), under a fixed tree layout:
`phase_{a,b}/ledger/NNNNNN.json`, `phase_{a,b}/runs/<run_id>/journal/<file>`, `tables/<table file>`,
`orphans/<run_id>/<file>`. Each commit's parent is the current ref head, so the history is linear.

The content of a boundary commit is taken only from a replay that reached the boundary's state (a consumed
attempt, a terminal state, or a published table). The one exception is a ledger-level closure, which commits
the run folder's files as found, under that closure. A commit is never otherwise built from a directory
listing alone.

**How commits are made.**

- The ref is `refs/g-route3/evidence`, created with `--create-reflog`.
- Commits use plumbing with a private `GIT_INDEX_FILE`: `hash-object -w`, `mktree`, `commit-tree`, then
  `update-ref <ref> <new> <expected-old>`. So they never touch the working branch, the shared index or hooks.

**Rules.**

- **Add-only.** A commit may add paths. If a path already exists in the ref with different bytes, the
  command refuses. That is tampering or damage, and it needs an operator ruling.
- **Never recreated.** The ref is created by the first G-ROUTE3 launch, before the first ledger entry.
  If the ref is missing but any ledger entry exists on disk, the command refuses and does not recreate it.
  Losing the ref is either history rewriting (out of scope) or an accident against which the fsync settings
  and reflog guard; it is a declared G4 exception that needs an operator ruling.
- **Retries.** A compare-and-swap conflict is re-read and retried up to 5 times. If `update-ref` reports
  failure, the ref is re-read; if it already names the new commit, the commit succeeded.
- **Unreadable ref.** If the ref or its objects cannot be read (for example a sharing violation on a pack),
  the command refuses. It never treats an unreadable ref as empty.
- **Stale ref lock.** A `refs/g-route3/evidence.lock` older than 10 minutes, while this command holds the
  G-ROUTE3 lease, is removed and logged. Every G-ROUTE3 writer of the ref holds that lease. Other tools in
  the shared repository do not write this ref; `pack-refs` in another worktree holds a ref lock for well
  under a second.
- **Pending commits.** A boundary commit that fails is recorded as **pending** in `recovery.log`. Its source
  of truth is the journal, so the commit can always be rebuilt. It is retried first by every later command.
  A consumption boundary that is still pending blocks all calls. A pending terminal boundary blocks the next
  launch, the table freeze and Phase B.

**Verification.** "On-disk equals committed" means: the set of file names in the run's `journal/` equals the
set under its committed path, and every file's bytes are equal. A ledger's on-disk entries must equal its
committed entries, and the committed ledger may not be longer (a longer one is restored, §9.1).

**Export.** The ref is not carried by clones or pushes of `main`. The evidence commit ids are bound into the
table and into Phase B's `run_created`. Pushing or bundling `refs/g-route3/evidence` for reviewers is a
documented operator step.

## 14. Publication protocol

To publish `path` with content `bytes`:

1. Write the bytes to `dir/.tmp-<n>-<token>`, then flush (`FlushFileBuffers`, or `fsync` on POSIX).
2. Rename into place:
   - **Windows:** `MoveFileExW(tmp, path, MOVEFILE_WRITE_THROUGH)` without `REPLACE_EXISTING`. Then open the
     directory with `GENERIC_WRITE | FILE_FLAG_BACKUP_SEMANTICS` and flush it.
   - **POSIX:** `link` then `unlink`, then `fsync` the directory. Or `renameat2(RENAME_NOREPLACE)` where it
     is available.
3. **Errors.**
   - **Before the rename:** a sharing violation (WinError 32), or access denied (WinError 5) *before* the
     rename, is retried up to 20 times at 100 ms intervals. After that the command aborts without
     publishing.
   - **After the rename:** if the rename succeeded but the directory flush failed, the entry **is
     published**. The flush is retried, and the failure is logged.
   - **Always:** after any error, the command re-lists the directory to decide whether the entry exists.
4. The lease token is re-read before every publication.
5. **Preflight** checks that directory flush works on the data volume.

Projections are written with the same protocol, replacing the previous projection in step 2.

## 15. The G-ROUTE3 lease

`data/g_route3/.lease` serializes everything in G-ROUTE3: both ledgers, every run, the table freeze, and
every write to the evidence ref. One lease for both phases matches "one local-model research job at a time",
and it means the evidence ref has exactly one writer.

The lease is published with §14 without replace. It holds a random token, the process id, the process
creation time (read with `PROCESS_QUERY_LIMITED_INFORMATION` on Windows, from `/proc` on POSIX), the host
name, and the **boot identifier**. On Windows that is the kernel's exact boot time
(`NtQuerySystemInformation(SystemTimeOfDayInformation).BootTime`, which does not drift with the clock
calculation); on POSIX it is `/proc/sys/kernel/random/boot_id`.

**When a lease is stale:**
- it was created in an earlier boot of this host; or
- on this host, in this boot, no process has that id; or
- a process has that id but a different creation time.

`ACCESS_DENIED` from `OpenProcess` counts as alive only when the boot identifier is the current one. `os.kill`
is never used. A lease from another host is never broken automatically. `--break-lease` breaks it with a
verbatim operator sentence and a recorded reason.

**Breaking a stale lease.** Rename the lease file to `.lease.broken-<token>` only if its bytes are still the
bytes that were observed. With no-replace, exactly one breaker wins. The winner creates a new lease and logs
the break.

## 16. Out of the journal

- **Telemetry and activity** (J10).
- **`recovery.log`.** It records lease breaks, retries, pending boundary commits and ref-lock removals. It
  is never read by a decision, except that pending boundary commits are recomputed from journals. The log
  only speeds that up.
- **Timestamps.**

## 17. Transport contract

Exactly one `POST /api/generate` per call. The adapter uses `max_retries=0` and follows no redirects. A test
uses a stub server that counts requests.

## 18. Write and crash table

| Write | After a kill or power loss at or just after it |
|---|---|
| `mkdir` of the run or journal | `absent` (R0). Launch continues, or the folder becomes an orphan. |
| Lease publish | Stale by the §15 rules |
| Lease break rename | Single winner. The loser retries. |
| `run_created` | `created`, or an orphan if there is no ledger entry |
| `attempt_consumed` | Boundary pending. It is committed before any call. |
| Consumption boundary commit | Pending until committed. No calls until then. |
| `call_started` k | `in_doubt(k)`, then closed |
| `call_recorded` k | Continue, close, or `awaiting_execution` |
| `execution_started` k | `execution_in_doubt`, then closed |
| `execution_recorded` k | Continue or close |
| `scoring_started` / `scored` / `completed` | Next derived entry. A torn one is re-derived. |
| `closed` | Terminal boundary pending, then the next attempt |
| Terminal boundary commit | Pending, retried first by every command |
| Rename to `.torn`; entry after `.torn` | `torn_pending`, then the entry. Idempotent. |
| Temporary file deletion or rename | Deleted only if identical, otherwise kept under a unique name |
| Ledger entries (all kinds) | Same rules as a run journal; the committed copy restores a lost tail |
| Orphan record commit, then folder move | Rerun `--clear-orphan`; idempotent |
| Table publish and commit | Identical rerun does nothing; a torn table is rebuilt identically |
| Projection publish | Rebuilt |
| Stale evidence lock removal | Logged; the commit is retried |
| `git hash-object` / `mktree` / `commit-tree` | Unreferenced objects; the boundary is still pending and is rebuilt |
| `update-ref` | Either the ref names the new commit (done) or the old one (pending) |
| Directory rename for `--clear-orphan` | Rerun; the orphan record is already committed and the rename is no-replace |

## 19. Verification

**Certification campaign (ruling 3).** It runs at freeze certification, and the freeze binds its report.

- **One choke point** for every filesystem write and every git plumbing call.
- **Starting scenarios.** The campaign starts from an uninterrupted synthetic run, and also from seeded
  scenarios: a transport failure, a sandbox failure, drift, abandon, clear-orphan, a declaration, a torn
  tail of each kind, a lost ledger tail, and a stale ref lock.
- **Kills.** It kills after every operation, and before every rename, then recursively kills again during
  recovery to a fixpoint.
- **Power loss.** It drops every operation not yet flushed, and reorders renames that were not flushed.
- **Interference.** It injects sharing violations, lease races with two processes, and a real git with
  injected locks and lost ref updates.

**Oracles:**
- the end state is `completed`, with fact payloads equal to those of the uninterrupted run; or `closed`
  with a truthful reason, after which the next attempt completes; or a declared refusal;
- J12: a stub provider counts calls per attempt and position, and every count is at most 1;
- no temporary file is deleted unless it is identical to its published entry;
- the disclosure is correct;
- the committed copies equal the journals;
- no hand edit is ever needed.

**Other tests:**
- **grammar-directed property tests**, covering every §5 rule and a mutation of every rule in §4.2;
- a **transport** test;
- a POSIX run of the protocol tests.

**Normal suite.** A quick, representative, deterministic subset of all the above.

## 20. Contract clauses this design supersedes

The following R6 clauses in `QUALIFICATION_CONTRACT.md`, the launcher documentation and the freeze are
replaced. The replacements will be reviewed with the implementation.

- **Authorization order.** R6 consumed the authorization only once the run existed and held its lease.
  Replaced by §9.2: lease, `run_created`, ledger, consumption boundary, calls.
- **Run completeness.** R6 required a manifest reading `complete` and a five-view terminal agreement.
  Replaced by replay state `completed` (§5).
- **Attempt and authorization binding.** R6 put attempt and authorization fields in every record. Replaced
  by `run_created` and the ledger.
- **Git anchoring.** R6 re-applied anchors on every command, with local commits by the launcher on the
  branch. Replaced by boundary commits to the evidence ref (§13).
- **Abandon.** R6's `--abandon --reason <free text>` is replaced by abandon on a failing preflight only
  (§9.3). R6's free-text orphan reason is replaced by an automatic orphan record.
- **Leases.** R6's manual removal of a stale lease is replaced by §15, including `--break-lease`.
- **Closures.** R6 said every non-complete end is anchored. Now it is committed at the terminal boundary.
- **Root agreement.** R6's ledger ↔ run-root agreement is replaced by the ledger, orphans and committed
  copies (§9).
- **Table schema.** `source.phase_a_attempts` becomes the §12 disclosure schema, with evidence commit ids.
- **Authorization sentence.** The new distinct sentence form is added (§9.4).
- **Guard evidence.** R6 kept a guarded digest per record. It is now observed in every `call_started`.

## 21. Operator decisions and rulings

**2026-09-24**

1. One append-only journal per run is the authoritative history. Everything else is a projection.
2. A torn write or full-disk event closes the attempt instead of repeating the call.
3. The exhaustive crash harness runs at freeze certification; a quick representative suite runs in
   development.
4. Review happens in two stages: the design, then the implementation.
5. The partial drafts stay untracked and unwired until the design is accepted. Existing code does not decide
   the architecture.

**2026-09-25**

6. Torn `scored` or `completed` entries are re-derived byte for byte. A mismatch is an integrity failure,
   never a closure. (Revision 3 makes this precise: the payload is compared, since the envelope of an entry
   republished at n+1 necessarily differs; torn `scoring_started` is re-derived the same way.)
7. `--abandon` is allowed only when the attempt is verified stuck. Partial results and cross-attempt output
   comparisons are disclosed.
8. Ruling 8 (evidence committed before every provider call) is **superseded by ruling 10**.
9. An integrity failure is recorded at ledger level, and the next attempt needs a distinct sentence. It is
   refused for protected attempts (§9.4).

**2026-09-25, after design review round 2**

10. **The code protects against accidents; tampering is caught at boundaries.** The code guarantees G1–G5
    against accidents and misuse of supported commands. Deliberate file edits between boundaries are out of
    scope for the code. At each attempt boundary and at the table freeze, the launcher commits the attempt's
    journal to git. The table freeze and Phase B verify every on-disk journal byte for byte against its
    committed copy. Per-call git evidence, high-water cross-checks and mid-run ref handling are removed.

## 22. Out of scope: grading changes

The five grading issues from the R6 fixture review are a separate scientific change with its own record and
review; see `EXTERNAL_REVIEW_ROUND6.md`. They are:

- dash and space normalization;
- a duplicate Answer line;
- a synthesis verbatim check;
- recursion and operator disclosure;
- a regex bound.

Provider generation calls for this design: **0**. Scientific runs launched: **0**.
