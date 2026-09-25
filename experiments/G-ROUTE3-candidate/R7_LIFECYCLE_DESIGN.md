# G-ROUTE3 R7 — journal/replay lifecycle architecture (design revision 5)

Status: **design-review candidate, revision 5.** Revisions 1 to 4 were each reviewed by two independent
reviewers and found not clean:

| Revision | Commit |
|---|---|
| 1 | `80a10d9` |
| 2 | `fd5c9f8` |
| 3 | `df78fa0` |
| 4 | `4499175` |

The findings, and the responses, are recorded in `R7_DESIGN_REVIEW_ROUND1.md` … `R7_DESIGN_REVIEW_ROUND4.md`.

Revision 5 answers round 4 with these changes:
- **The data root belongs to the experiment, not to a freeze.** Attempts and disclosure span freezes, and a
  new freeze cannot restart the ledgers (§3, §9.3).
- **The data root is set up atomically,** with a root evidence commit, before any ledger entry exists (§3.1).
- **Protection is based on sealed evidence of collection, not on the chain,** so damage can never unprotect a
  finished collection (§9.4).
- **Interrupts never close a finished collection** (§7).
- **Children run isolated.** The sandbox, scorer and git run in a kill-on-close job, and the sandbox is shielded
  from console signals (§8, §15).
- **Restores are staged outside the verified folders,** and damaged files are quarantined elsewhere (§13.4).

Nothing scientific changes: corpora, gold, validators, prompts, the qualification rule, routing, gates,
thresholds and denominators all stay as they are. The sandbox's grading of a normal child exit is unchanged
(§8). Grading changes are out of scope (§22). No implementation is wired in, no execution freeze is written,
no provider is contacted, and no scientific run is launched.

**Review sequence.**
1. Design review of this revision.
2. If clean, implementation from this document.
3. Implementation review, including the certification crash campaign.
4. Only then is an R7 execution freeze offered for authorization.

---

## 1. Guarantees and threat model

One G-ROUTE3 phase attempt sends a fixed-seed schedule of provider calls: 288 for Phase A, 144 for Phase B.

| | Guarantee |
|---|---|
| **G1** | **At most once.** No schedule position is sent to the provider twice within one attempt. |
| **G2** | **Truthful history.** Anything unproven is recorded as uncertain and disclosed, never guessed. Host-caused failures are never recorded as model failures. |
| **G3** | **No best-of-N.** A completed attempt, or an attempt with sealed evidence that its collection finished, cannot be discarded or replaced, whatever the freeze. Every non-complete attempt is disclosed as one where optional stopping cannot be excluded. |
| **G4** | **A way forward.** Every reachable state has a supported command that leads to completion or to a recorded closure. The only exceptions are declared (§1.3), and each needs an operator ruling. |
| **G5** | **Determinism.** Replay is a pure function of the entry files. Derived entries re-derive to identical payloads. |

### 1.1 What the code defends against (operator ruling 10)

G1–G5 hold against **accidents** and against **misuse of supported commands**. Accidents include:
- crashes, kills and power loss;
- a full disk, damaged files, and transient read errors;
- sharing violations;
- Ctrl+C;
- `git clean`, `stash` and `gc` in any checkout;
- git lock files left behind.

**Tampering is caught at boundaries.** Each attempt's files are committed to the evidence repository at its
boundaries and at the table freeze (§13). Every command verifies every committed file against that repository
before it acts (§13.4).

### 1.2 Declared residuals

These are trust assumptions, stated openly:

- **Tampering with an attempt in progress.** "In progress" means consumed, with no committed terminal
  boundary. Deliberately editing, deleting or planting files of such an attempt is not prevented by the code.
  Launch runs collection, scoring and completion in one process and commits the terminal boundary before
  returning. The window is therefore the run itself, plus any time after an interruption.
- **Antivirus deleting the trailing `call_started`.** An antivirus that silently deletes the last journal file
  of a running attempt could cause a call to repeat. `call_started` holds only digests, so this is
  implausible. The runbook excludes `D` from scanning.
- **Out of scope, as before:** a fake model server, a second copy of `D`, rewriting the evidence
  repository's history, or deleting `D` as a whole.

### 1.3 Declared exceptions to G4

Each of these blocks the phase until an operator ruling:
- a persistent scorer defect (§6);
- an integrity failure of a protected attempt (§9.4);
- a ledger that replays to `integrity_failure` (§9.1);
- a committed sealed entry whose on-disk copy seals but differs, or an add-only conflict (§13.4);
- `D` existing without an intact evidence repository (§3.1).

## 2. Invariants

- **J1 — authority.** Each run has one append-only **journal**. Each phase has one append-only **ledger** of
  attempts (§9). Every other file is a projection, a committed copy, a snapshot, or a non-authoritative log.
- **J2 — sealed chain.** Every entry is sealed with its canonical digest (§4.4) and names the seal of the
  last valid entry before it (§4.1).
- **J3 — durable, non-overwriting publication.** Entries are published only by the §14 protocol. No
  irreversible action depends on an entry until it is **durable**.
- **J4 — pure replay.** `replay(entry files) → (state, observations)` is a pure, total function of the
  `NNNNNN.json` and `NNNNNN.torn` files of one journal. It never writes, never reads git, and never reads
  other files. Repairs are made only by `recover()` and by verification (§13.4), and only by the lease
  holder.
- **J5 — facts only.** Entries hold facts. Nothing recomputable is stored.
- **J6 — always sealable.** Every value passes through `safe_value`. Raw model text is stored as base64
  plus the sha256 of its text.
- **J7 — deterministic derivations.** Derived payloads (`scoring_started`, `scored`, `completed`) are pure
  functions of sealed inputs. Every re-derivation is compared by **payload**, and only against sealed or
  committed data.
- **J8 — one command shape.** Every command runs these steps in order:
  1. take the lease (§15);
  2. verify committed evidence (§13.4);
  3. replay the ledgers and runs;
  4. recover to a fixpoint (§6);
  5. complete pending boundary commits (§13.3);
  6. decide and act, running the drift check before any derivation, sandbox run or call;
  7. commit any boundary the action reached, before returning.
- **J9 — way forward.** G4. §19 checks it mechanically.
- **J10 — inert telemetry.** Activity, telemetry and `recovery.log` are never read by any decision.
- **J11 — boundary evidence.**
  - No `call_started` of an attempt is published before its consumption boundary is committed.
  - A terminal entry's boundary is committed before the command that wrote it returns success.
  - If that commit fails, the boundary stays pending, and J8 step 5 of every later command completes it.
- **J12 — at most once.** A request is sent only after its `call_started` is durable. The next entry number
  is unique, and publication never overwrites, so no second `call_started` for a position can exist. A
  started call whose outcome is not durably recorded closes the attempt. The call is never repeated.
- **J13 — nothing closes a finished collection.** Once every position is recorded and executed cleanly (the
  state `collected`), only `scoring_started`, `scored` and `completed` may follow. From `collected` onward,
  drift, scorer failures and interrupts make commands **refuse or exit**. They never close the attempt.
- **J14 — zero transport retries.** Exactly one HTTP request is made per call (§17).

## 3. Files

The **data root** `D` is a constant of the G-ROUTE3 experiment. It is an absolute local path outside every git
checkout, named in the qualification contract, and recorded in every execution freeze. The proposed path is
`%LOCALAPPDATA%\Eidolon\research\g_route3`. That parent folder already exists as the desktop app's data
folder; the app touches only its own `data` and `runtime` subfolders.

The freeze writer refuses to name any other `D`. Every checkout and every freeze uses the same `D`. Preflight
refuses a network volume.

```
D/
  root.json                       {"experiment": "G-ROUTE3", "root_id": <random>}; committed in the root commit
  .lease                          the lease file (§15)
  evidence.git/                   private bare git repository (§13)
  recovery.log                    non-authoritative
  staging/                        temp files for restores (§13.4)
  quarantine/<token>/…            damaged files moved aside by verification (§13.4)
  tables/                         the qualification table and its audit copy (§7)
  phase_a/, phase_b/
    ledger/NNNNNN.json | .torn | .tmp-* | .orphan-tmp-*
    runs/<run_id>/journal/NNNNNN.json | NNNNNN.torn | .tmp-* | .orphan-tmp-*
    runs/<run_id>/score.json, receipt.json       projections (§14)
    orphans/<run_id>-<token>/                    cleared orphan folders (§9.4)
```

### 3.1 Setup

The first launch of G-ROUTE3 sets `D` up **atomically**:
1. Build `D.setup-<token>` next to `D`, containing:
   - `root.json`;
   - the empty folders;
   - `evidence.git`, with its config (§13.1) and a **root commit** holding `root.json` on
     `refs/heads/evidence`.
2. Flush every file and folder in it.
3. Rename it to `D` without replace.
4. Flush the parent folder.

`D` therefore either does not exist or is complete. Leftover `D.setup-*` folders are removed by the next setup
attempt. If `D` exists but `evidence.git`, its ref or its root commit is missing or unreadable, the command
refuses (§1.3). `root.json` is a committed item: it is restored (§13.4) and never regenerated.

Replay considers only `NNNNNN.json` and `NNNNNN.torn` files. Every other file is reported and ignored.

## 4. Journal entries

### 4.1 Envelope

```json
{"entry": n, "kind": "…", "run_id": "…", "previous_entry_sha256": "…",
 "acknowledges": [{"entry": m, "sha256": "…"}, …], "orphans": [{"name": "…", "sha256": "…"}, …],
 "payload": {…}, "record_sha256": "…"}
```

- **`previous_entry_sha256`** is the seal of the last **valid** entry before n, skipping `.torn` entries.
  - For a run's entry 1, it is the seal of the ledger head that `run_created` claims to follow.
  - For a ledger's entry 1, it is the **genesis seal**: the canonical digest of
    `{"genesis": "g-route3-ledger", "phase": "A" | "B", "root_id": …}`.
- **`acknowledges`** lists every `.torn` entry between the last valid entry and n, with the sha256 of its
  bytes.
- **`orphans`** names `.orphan-tmp-*` files of this directory that no earlier entry named.
  - The publisher checks that they exist when it publishes.
  - Replay checks only that each name appears once across the journal (J4).

Both lists sit in the envelope, so a derived entry's payload stays equal to its re-derivation.

The **next entry number** is the highest occupied number, whether `.json` or `.torn`, plus 1.

No seal contains a timestamp.

### 4.2 Kinds

| Kind | Payload | May follow (the last valid entry) |
|---|---|---|
| `run_created` | Phase, attempt number, authorization digest and sentence sha256, claimed ledger head, freeze binding, schedule, guarded and freeze digests, `root_id`, synthetic flag, fixed endpoint, model receipts, transport contract. For Phase B, also the table digest, the Phase A run id, and the evidence commit id bound into the table. | Nothing: it is entry 1 |
| `call_started` | Position k, call id, request digest, guarded digest observed now | `run_created` (k = 1); a clean non-coding `call_recorded` k−1; a clean `execution_recorded` k−1 |
| `call_recorded` | Position k, equal to the preceding `call_started`. Provider raw body (base64) and its sha256; raw output (base64) and the sha256 of its text; returned model; scalar metrics; `transport_failure` (empty unless the provider boundary raised). | `call_started` k |
| `execution_started` | Position k, candidate digest | A clean coding `call_recorded` k |
| `execution_recorded` | Position k, sandbox evidence, candidate error, `infrastructure_failure` (empty, `execution_interrupted`, `sandbox_host_failure:<detail>`) | `execution_started` k |
| `scoring_started` | Digest of the fact prefix. For Phase B, the seals of the disclosure inputs: the ledger head, and every earlier attempt's terminal entry. | `collected` |
| `scored` | The score report: a pure function of the inputs named in `scoring_started` (§4.3) | `scoring_started` |
| `completed` | Receipt: chain head seal, `scored` seal, `run_created` seal, freeze and guarded digests | `scored` |
| `closed` | A reason (below); `calls_started`, `calls_recorded`, `executions_started`; the in-doubt position if any; the exception class and message if any | Any entry from `run_created` up to, but not including, `collected` (J13) |

**`closed` reasons.** Each reason has one source:

| Reason | Source |
|---|---|
| `transport_failure` | `call_recorded.transport_failure` is non-empty |
| `infrastructure_failure` | `execution_recorded.infrastructure_failure` is `sandbox_host_failure:*` |
| `execution_interrupted` | `execution_recorded.infrastructure_failure` is `execution_interrupted` |
| `call_outcome_unknown` | A `call_started` with no record |
| `durability_uncertain` | A torn entry that cannot be re-derived |
| `operator_interrupt` | An interrupt before `collected` (§7) |
| `abandoned_preflight_failed:<checks>` | §9.3 |

Every non-complete attempt is disclosed with **"optional stopping cannot be excluded"** (§12). A call is never
retried.

### 4.3 Determinism

The inputs to `scored` are:
- the sealed fact entries of this run;
- the frozen corpora, gold and table, bound by the digests in `run_created`;
- for Phase B's attempt disclosure, the sealed ledger entries and the earlier attempts' terminal entries whose
  seals `scoring_started` names. These are committed (§13), so they cannot change unnoticed.

A re-derivation that does not reproduce the same payload is an integrity failure, never an overwrite.

### 4.4 Canonical JSON

A seal is the sha256 of `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
allow_nan=False).encode("utf-8")`, where `value` is the envelope without `record_sha256`, passed through
`safe_value`. Integers of 10^30 or more become strings. Floats use the shortest round-trip `repr`.

**Reading.** An error while reading a file (a sharing violation or an I/O error) is retried up to 20 times at
100 ms intervals, and after that the command refuses. Only bytes actually read can be judged torn.

## 5. Replay: an ordered, total decision procedure

**Inputs.** The entries are the `NNNNNN.json` and `NNNNNN.torn` files. An `n.json` whose bytes equal an existing
`n.torn` is treated as that `.torn` alone, and recovery unlinks the `.json`.

**Terms.**
- The **trailing tear** is the maximal run of `.torn` entries at the highest numbers.
- The **last valid entry** is the highest-numbered entry that parses and seals.

Rules apply **in order; the first match wins**:

| # | Condition | State |
|---|---|---|
| R0 | No `journal/` folder, or no entries in it | `absent` |
| R1 | The numbers 1 … highest are not each occupied exactly once, or an `n.json` and an `n.torn` differ | `integrity_failure` |
| R2 | A `.json` entry, other than the highest-numbered one, fails to parse or seal | `integrity_failure` |
| R3 | A sealed entry fails a grammar or payload check (below) | `integrity_failure` |
| R4 | A `.torn` outside the trailing tear is not in the next valid entry's `acknowledges`. Or, in a run journal, entry 1 is `.torn` and a valid entry exists | `integrity_failure` |
| R5 | The highest-numbered `.json` fails to parse or seal | `torn_tail(n)` |
| R6 | A trailing tear exists | `torn_pending(T, predicted)` |
| R7 | The last entry is `completed` | `completed` |
| R8 | The last entry is `closed` | `closed` |
| R9 | The last entry is `scored` | `scored` |
| R10 | The last entry is `scoring_started` | `scoring_interrupted` |
| R11 | The last entry is `execution_started` k | `execution_in_doubt(k)` |
| R12 | The last entry is `call_started` k | `in_doubt(k)` |
| R13 | The last entry carries a failure field | `faulted(k)` |
| R14 | The last entry is a clean coding `call_recorded` k | `awaiting_execution(k)` |
| R15 | Every position is recorded and executed cleanly | `collected` |
| R16 | The last entry is a clean record of k, with k less than N | `collecting(k)` |
| R17 | The last entry is `run_created` | `created` |

**Grammar and payload checks (R3)** apply to every sealed entry, **including the last**:
- the entry number equals the file name, and the run id is constant;
- `previous_entry_sha256` names the last valid entry before it;
- `acknowledges` lists exactly the `.torn` entries in between, with their sha256;
- no `orphans` name appears twice;
- the kind follows §4.2;
- positions and call ids match the schedule;
- nothing follows `completed` or `closed`;
- `closed` never follows `collected`;
- only `closed` follows a failure field;
- the `completed` receipt matches the chain.

**Predicting a trailing tear (R6).** The prediction comes from the last valid entry and the fact prefix. Every
`.torn` in the tear gets the same prediction.

| Last valid entry | Predicted kind | Class |
|---|---|---|
| None (the tear starts at entry 1) | `run_created` | special (§6) |
| `run_created`, or a clean record of k less than N | `call_started` | provider |
| `call_started` k | `call_recorded` | provider |
| A clean coding `call_recorded` k | `execution_started` | provider |
| `execution_started` k | `execution_recorded` | provider |
| A record carrying a failure field | `closed`, with that failure's reason (§4.2) | closure |
| A clean record completing position N (`collected`) | `scoring_started` | derived |
| `scoring_started` | `scored` | derived |
| `scored` | `completed` | derived |
| `completed` or `closed` | Nothing is ever written after a terminal entry, so this is damage or tampering: `integrity_failure` | — |

Torn bytes are never parsed for decisions.

## 6. `recover()`: one step at a time, by the lease holder

- Every recovery rename, unlink or deletion is followed by a directory flush before the next step.
- `recover()` never runs the sandbox or the scorer. Those run only as actions of `--resume` and launch (§7),
  after the drift check.
- Runs closed at ledger level are frozen, and `recover()` never touches them.

| State | Recovery step |
|---|---|
| `torn_tail(n)` | Rename `n.json` to `n.torn` without replace. If an identical `n.torn` exists, unlink `n.json` instead. |
| `torn_pending(T, provider)` | Publish `closed(durability_uncertain)` after the tear, acknowledging T |
| `torn_pending(T, closure)` | Publish `closed(<the failure's reason>)` after the tear, acknowledging T |
| `torn_pending(T, derived)` | Drift check, then re-derive the entry and publish it after the tear, acknowledging T. If a committed copy of that kind exists, the payloads must be equal; a mismatch is an integrity failure. Under drift, stop without writing and leave the state for `--resume`, which refuses until the files are restored. |
| `torn_pending(T from 1, run_created)`, or `absent`, with a ledger entry and the consumption boundary **not** committed | No call can have been made. Publish `attempt_closed_at_ledger(durability_uncertain)` with a snapshot (§9.1). |
| `torn_pending(T from 1, run_created)` with the consumption boundary committed | `integrity_failure` (§9.4) |
| No ledger entry names this run | An orphan (§9.4). `recover()` does nothing. |
| `in_doubt(k)` | Publish `closed(call_outcome_unknown, in_doubt=k)` |
| `execution_in_doubt(k)` | Publish `execution_recorded(k, infrastructure_failure=execution_interrupted)`. `faulted` then closes the attempt as `execution_interrupted`. The sandbox is never re-run. |
| `faulted(k)` | Publish `closed(<the failure's reason>)` |
| `created`, `collecting`, `awaiting_execution`, `collected`, `scoring_interrupted`, `scored` | No step: these are left for §7 |

**Temporary files.**
- A `.tmp-*` file whose bytes equal the entry published at its number is deleted.
- Any other `.tmp-*` file is renamed to `.orphan-tmp-<n>-<token>`. The next entry published in that folder
  names it. If the folder is terminal, the terminal commit carries it instead. Orphan temporary files are
  committed with the journal. No provider output is ever deleted.

## 7. Commands

Every command follows J8. "Sentence" refers to §7.1. The table gives what each command does in each state
after recovery.

| State after recovery | launch n | `--resume` n | `--abandon` n | `--declare-integrity-failure` n |
|---|---|---|---|---|
| No run, attempt n not consumed | Allowed when §9.3 holds: publish `run_created` and make it durable, publish `attempt_consumed`, commit the consumption boundary, then collect, score and complete | refused | refused | refused |
| `created`, `collecting`, `awaiting_execution` | refused | Drift check, then collect | Allowed only on a failing preflight (§9.3) | refused |
| `collected`, `scoring_interrupted`, `scored` | refused | Drift check, then score and complete | refused | refused |
| `completed` | refused | Re-project only | refused | **refused** |
| `closed`, or closed at ledger level | The next attempt | refused | refused | refused |
| `integrity_failure`, or `absent` with the consumption committed | refused | refused | refused | Allowed unless protected (§9.4) |
| A run folder without a ledger entry | refused | refused | refused | refused (`--clear-orphan` instead) |

**Drift.** In any state, drift refuses until the guarded files are restored. The refusal names the paths and
digests, and it never closes anything.

**Scoring.** The scorer runs in an isolated child (§8) with a timeout. If it succeeds, `scored` is published.
If it fails, the command refuses (J13). The scorer is provider-free and deterministic, so a failure that
persists is a defect (§1.3).

**Interrupts.** The handler for SIGINT, SIGTERM and CTRL_BREAK only sets a flag. The main loop checks the flag
at two safe points:
- **before each `call_started`**;
- **after each record whose state is not `collected`.**

If the flag is set at either point, the loop publishes `closed(operator_interrupt)` through the normal path and
exits. A request already in flight is completed and recorded first. If the flag is set once the state is
`collected` or later, the process exits **without writing**, and `--resume` then scores. A second signal, or a
hard kill, leaves the state for the next command to classify.

**Attempt numbers.** A launch's n must equal the number of attempts ever consumed in the phase, across all
freezes, plus 1. `--resume n` requires n to be the latest consumed attempt, and is refused if a later attempt
exists. The run id comes from the ledger.

**`--freeze-table`** runs after J8 steps 1–5. Those steps have already verified every committed item.
1. It requires:
   - the named Phase A attempt to be `completed`, with its terminal boundary committed;
   - every other Phase A attempt to be closed or closed at ledger level;
   - no Phase A attempt to be in progress.
2. It builds the table deterministically from the replayed `scored` entry. The table records:
   - the attempt's run id;
   - its `run_created` and `scored` seals;
   - the evidence commit id of its terminal boundary.
3. It checks the audit document. The document must read `READY`, name the run and the score digest (as in R6),
   and name both seals. Its sha256 must not equal any frozen artifact's digest in the freeze. Its bytes are
   copied to `D/tables/`.
4. It publishes the table and the audit copy with §14, without replace, then commits them in the table-freeze
   commit.
5. A rerun that finds the identical table does nothing. A different table is refused.

After the freeze, the operator commits a copy of the table to `main` at
`experiments/G-ROUTE3-candidate/QUALIFICATION_TABLE.json` (§10.9).

**`--clear-orphan`** is described in §9.4.

### 7.1 Sentences

Each sentence is matched as a full string.
- `<binding>` must equal the execution-freeze digest in force.
- `<table>` must equal the frozen table's digest.
- `<P>` is `A` or `B`.
- Numbers have no leading zeros.

| Command | Sentence |
|---|---|
| Launch, Phase A | `Authorize G-ROUTE3 phase A execution <binding> attempt <n>` |
| Launch, Phase B | `Authorize G-ROUTE3 phase B execution <binding> table <table> attempt <n>` |
| Launch after a ledger-level `integrity_failure` or `journal_missing` of attempt n−1 | The launch form, followed by ` after integrity failure of attempt <n-1>` |
| `--resume n` | Byte-identical to the sentence consumed for attempt n |
| `--abandon n` | `Abandon G-ROUTE3 phase <P> attempt <n> after failed preflight` |
| `--declare-integrity-failure n` | `Declare G-ROUTE3 phase <P> attempt <n> integrity failure` |
| `--clear-orphan` | `Clear G-ROUTE3 phase <P> orphan run <run_id>` |
| `--freeze-table` | `Freeze G-ROUTE3 qualification table from phase A attempt <n> of execution <binding>` |

The distinct launch form is required exactly when attempt n−1 was closed at ledger level as `integrity_failure`
or `journal_missing`. In that case the ordinary form is refused, and otherwise the distinct form is refused.
Only launch sentences authorize provider contact. Every sentence is Marcus's to give; none is ever self-issued.

## 8. One call

1. Check the guard (drift).
2. Publish `call_started` k and make it **durable** (§14). If it cannot be made durable, exit without sending.
   The next command then finds `in_doubt(k)` and closes the attempt.
3. Send exactly one request (J14).
4. Publish `call_recorded` k, with `transport_failure` set if the provider boundary raised.
5. For a coding call:
   - Publish `execution_started` k and make it durable.
   - Run the sandbox once in an **isolated worker child** (below).
   - Publish `execution_recorded` k.
6. If a failure field is set, publish `closed`.

No git operation happens inside the per-call loop.

**Isolated children.** The sandbox worker, the scorer, and every git process run as children of the lease
holder:
- **Job object.** On Windows they run in a job object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. On POSIX they
  run in their own process group, which the holder kills on exit, with `PR_SET_PDEATHSIG` on Linux. A dead
  holder therefore leaves no live children.
- **Console signals.** The sandbox worker is started with `CREATE_NEW_PROCESS_GROUP` on Windows, which disables
  Ctrl+C for it and for its descendants, or `start_new_session` on POSIX. So a console interrupt never reaches
  the candidate's test process.
- **Inside the worker.** The worker calls the unchanged `run_isolated_fixture`, so the grading of a normal
  child exit is exactly as in R6.
- **Host failures.** A worker that dies, times out at the worker level, or reports a test exit caused by a
  signal or a console control is recorded as `infrastructure_failure=sandbox_host_failure:<detail>`, never as
  a model failure. A console-control test exit is Windows `0xC000013A`; a signal exit is a negative return
  code on POSIX.

## 9. Attempts: the ledger

### 9.1 Ledger entries

Each phase has one ledger in `D/phase_X/ledger/`, spanning every freeze. It is a hash-chained journal with the
same envelope, protocol, reading rules, temporary-file handling, and rules R0–R6 as a run journal, except:
- it starts from the genesis seal;
- R4's entry-1 clause does not apply.

It has three kinds:
- **`attempt_consumed`:** attempt number, the verbatim sentence, freeze binding, authorization digest, run id,
  and the `run_created` seal.
- **`attempt_closed_at_ledger`:** attempt number, reason (`integrity_failure`, `journal_missing` or
  `durability_uncertain`), and what was observed. Its counts are **unknown**, with lower bounds, partial cells
  and output identity taken from the individually sealed records in the **closure snapshot**. The snapshot is
  the run folder's files as found, committed under `closures/<phase>/<attempt>/` (§13.1). A run closed at ledger
  level is frozen.
- **`ledger_torn_acknowledged`:** acknowledges a torn ledger tail that was never committed. It has one
  deterministic rule:
  - If a run folder exists whose `run_created` claims the ledger head before the tear, the torn entry was that
    run's `attempt_consumed`. The acknowledgement records attempt n = consumed count + 1 as consumed and closed
    `durability_uncertain`, with that run id. No call can have been made, because J11 requires the consumption
    commit first.
  - Otherwise the torn entry was a closure or an acknowledgement. Nothing is closed, and the condition that
    produced it recurs, or is re-declared.

**Committed copies win.** A torn or missing ledger entry that has a committed copy is restored byte for byte
(§13.4), never acknowledged. A ledger that replays to `integrity_failure` blocks the phase (§1.3).

### 9.2 Order at launch

1. Take the lease. Set up `D` if it does not exist (§3.1).
2. Publish `run_created`, whose previous seal is the ledger head it claims, and make it durable.
3. Publish `attempt_consumed`, naming the `run_created` seal.
4. Commit the **consumption boundary**: every uncommitted ledger entry, plus `000001.json` (§13).
5. Collect, score and complete in the same process, then commit the terminal boundary.

**If interrupted:**

| Point | Effect |
|---|---|
| Between 2 and 3 | An orphan with no calls |
| Between 3 and 4 | Pending. J8 step 5 commits it if the run replays to `created`. Otherwise §6 closes it at ledger level; no call was possible. |

### 9.3 Attempt policy

- **Launch.** Attempt n+1 may be launched only when every earlier attempt of the phase, under **any** freeze,
  is `closed` or closed at ledger level.
  - Launch is refused if any earlier attempt replays as `completed`, or has a committed `completed` copy.
  - Launch is also refused if any earlier attempt is protected (§9.4) and not closed.
  - The first `completed` attempt is the result.
- **New freezes.**
  - A new execution freeze cannot reset anything: `D`, the ledgers and the disclosure are shared by every
    freeze.
  - The freeze writer refuses once `D` holds a table, or any attempt that is protected or `completed`. This
    carries over R6's "no new freeze once a table exists".
  - Each `run_created` and `attempt_consumed` records its freeze binding, and the disclosure lists every
    attempt under every binding.
- **Abandon.**
  - `--abandon` is allowed only when the command's own preflight fails with a **persistent** condition:
    - the model receipts differ from the frozen bindings;
    - the receipts cannot be read after a bounded wait of 10 minutes;
    - the freeze no longer verifies.
  - Drift is not a preflight failure, because it refuses until the files are restored.
  - The closure names the failing checks.
  - Abandon is an optional stop, and it is disclosed like one.

### 9.4 Integrity failures, missing journals, orphans

**Protection.** An attempt is **protected** when any of these holds:
- it has a committed terminal copy;
- **any individually sealed entry** on disk, or in a committed copy, or in a closure snapshot, is:
  - a `call_recorded` or `execution_recorded` of position N;
  - a `scoring_started`, a `scored` or a `completed`.

  Each file is checked on its own, independent of the chain, so damage elsewhere cannot hide a finished
  collection;
- it is the Phase A attempt a frozen table names.

Every ledger-level closure, whether declared by `--declare-integrity-failure` or automatic (§6, §9.1), is
**refused** for a protected attempt. A refusal blocks the phase until an operator ruling (§1.3). The
automatic closures apply only when no call was possible, so they never meet a protected attempt.

**`--clear-orphan`** accepts only a run folder that has no `call_started` and no ledger entry.
1. It commits an orphan snapshot under `orphans/<phase>/<run_id>/`.
2. It then moves the folder to `phase_X/orphans/<run_id>-<token>/` with a no-replace folder rename:
   `MoveFileExW` without replace on Windows, and on POSIX `renameat2(RENAME_NOREPLACE)`, or failing that
   `mkdir` plus per-file no-replace moves.
3. A rerun is idempotent.

Moved orphan folders are verified against their snapshots (§13.4). Orphans are disclosed.

## 10. Phase B preconditions

Phase B may contact the provider only when all of the following hold. J8 step 2 has already verified every
committed item.

1. The named Phase A attempt replays as `completed`, with its terminal boundary committed.
2. It is the only completed Phase A attempt. Every other Phase A attempt, under any freeze, is closed or closed
   at ledger level, and none is in progress.
3. Its `run_created` attempt, authorization digest and sentence digest equal its ledger entry, and the ledger
   entry names the `run_created` seal.
4. It is not synthetic, and it ran under this freeze. Its guarded digest, in `run_created` and in every
   `call_started`, equals today's. Its model receipts verify, and its endpoint is the fixed one.
5. The provider evidence of every call is consistent: body digest, model, output, and request digest against
   the schedule.
6. Cells re-derived from its facts equal both its `scored` cells and the table's cells.
7. **Table checks (the full R6 `verify_table` and `phase_b_preconditions` set, plus R7 additions):**
   - **Integrity:**
     - the schema version;
     - the digest recomputes.
   - **Cells:**
     - exactly 72 cells;
     - every verdict is in {QUALIFIED, NOT_QUALIFIED, INSUFFICIENT};
     - the routing lookup is exactly what the cells imply;
     - the table was derived from Corpus A alone (`corpus_b_consulted` false).
   - **Bindings:**
     - the corpus, gold and threshold digests match;
     - the table is bound to this freeze.
   - **Audit:**
     - it reads `READY`;
     - it names the run and the score digest, and both seals;
     - its document sha256 equals the committed audit copy;
     - its document sha256 differs from every frozen artifact's digest in the freeze.
   - **R7 additions:**
     - the table's run id and seals equal the named attempt's;
     - the table names the evidence commit that holds the attempt's terminal copy, and that commit is an
       ancestor of the evidence head.
8. The table's attempt disclosure equals the disclosure computed now (§12, excluding the restore log).
9. A read-only git check finds that `main`, in the checkout, contains a commit whose
   `experiments/G-ROUTE3-candidate/QUALIFICATION_TABLE.json` has exactly the table's bytes.
10. The Phase B sentence names the freeze, the table and attempt n, and is consumed through §9.
11. `D/tables/<table>` is inside Phase B's per-call guard.

## 11. Durability

- **G1 needs no git.** It rests on `call_started` being durable before the request (§14), and on the unique
  next entry number.
- **Entries before irreversible steps.** Every journal and ledger entry is durable before any irreversible step
  that depends on it. Irreversible steps are a request, the sandbox, and a boundary commit that names the
  entry.
- **Boundary commits.** Boundary commits are durable before a command reports success.
  - The evidence repository uses the `files` ref backend, with `core.fsync=all`, `core.fsyncMethod=fsync`,
    `gc.auto=0` and `core.logAllRefUpdates=always` in its own config. Every command checks these settings.
  - Git 2.38 or later is required.
  - The ref directory is flushed after `update-ref`.
  - Only the lease holder's children run git in the repository.
- **Accidental losses are recorded, never guessed:**
  - an in-doubt call closes the attempt;
  - a torn entry stays in place;
  - an unmatched temporary file is kept under a unique name;
  - a damaged committed file is quarantined and restored from its commit.

## 12. Disclosure

For every attempt of the phase, under every freeze, including ledger-level closures and cleared orphans, the
disclosure records:
- the attempt number, the freeze binding, the run id, the outcome and the closure reason;
- the flag **"optional stopping cannot be excluded"** on every non-complete attempt;
- `calls_started`, `calls_recorded`, `executions_started`, and the in-doubt position if any. For ledger-level
  closures these are **unknown**, with lower bounds from the closure snapshot;
- **partial results:**
  - for Phase A, cells re-derived from the recorded calls;
  - for Phase B, per-observation correctness and the routing decisions that can be determined.

  For ledger-level closures, these come from the snapshot's individually sealed records, labelled as such;
- for every seeded position recorded in more than one attempt, whether the raw-output sha256 values are
  identical. Where no sealed record exists, it is marked **undeterminable**;
- the evidence commit id of each boundary.

**Where the disclosure appears:**
- The qualification table and the Phase B score contain it.
- **In addition, a phase disclosure record is committed at every terminal and ledger-closure boundary**, under
  `disclosure/<phase>/<commit sequence>.json`. The runbook requires publishing the latest one whether or not
  any attempt completes.
- The restore log (§13.4) is disclosed alongside it, but kept out of the §10.8 comparison.

## 13. The evidence repository

### 13.1 Layout and commits

`D/evidence.git` is created by setup (§3.1) with the config in §11. Its single ref is `refs/heads/evidence`,
with linear history starting at the root commit. Each commit's tree holds `root.json`.

The tree layout is:

```
root.json
phase_{a,b}/ledger/<file>
phase_{a,b}/runs/<run_id>/journal/<file>        every file in the journal folder
closures/<phase>/<attempt>/<file>               closure snapshots
orphans/<phase>/<run_id>/<file>                 orphan snapshots
tables/<table>, tables/<audit copy>
disclosure/<phase>/<sequence>.json
quarantine/<token>/<path>                       damaged files moved aside by §13.4
```

Every boundary commit also adds every uncommitted ledger entry below its own, and every uncommitted
quarantine file. The boundaries are:

| Boundary | When | Adds |
|---|---|---|
| **Consumption** | After `attempt_consumed`, before any `call_started` | `000001.json` |
| **Terminal** | After `completed` or `closed` | Every file in the run's `journal/`, plus a disclosure record |
| **Ledger closure** | After any ledger-level closure | The closure snapshot, plus a disclosure record |
| **Orphan** | Before an orphan folder moves | The orphan snapshot |
| **Table freeze** | After the table is published | The table and the audit copy |

**Where commit content comes from.** A commit's content comes only from a replay that reached the boundary's
state. For a snapshot, it comes from the files as found.

**How commits are made.** Commits use plumbing with a private index: `hash-object -w`, `mktree`, `commit-tree`,
then `update-ref <ref> <new> <expected-old>`.

### 13.2 Rules

- **Add-only.** If a path already exists with different bytes, the command refuses (§1.3).
- **Unreadable.** If the repository, the ref, the root commit or the config cannot be read, or the config is
  wrong, the command refuses. An unreadable repository is never treated as empty.
- **Locks.** Only the lease holder's children run git in the repository, and a dead holder's children are
  killed by the job (§8). Any `*.lock` file the holder finds there is therefore stale. It is removed and
  logged.
- **Retries.** If `update-ref` reports failure, the ref is re-read. If it already names the new commit, the
  commit succeeded. Otherwise the commit is retried up to 5 times, then left pending.

### 13.3 Pending boundaries

A boundary is **pending** when a replayed state requires a commit that the ref does not yet hold. Pending
boundaries are computed from replay in J8 step 5.
- A pending consumption boundary blocks all calls of that attempt.
- A pending terminal boundary blocks the next launch, the table freeze and Phase B.
- A pending consumption boundary is superseded by the §6 ledger-level closure **only** when the run has no
  valid entry (`absent`, or a tear from entry 1).
- Any other run that cannot be committed as it replays is an integrity failure (§9.4).

### 13.4 Verification (every command, J8 step 2)

Every committed file is compared **byte for byte** with its copy on disk. For the committed journal of a
**terminal** run, the set of `NNNNNN.*` entries must also be equal. Files other than entries in a journal
folder are not counted as extra.

| On-disk copy | Action |
|---|---|
| Identical | Nothing |
| Missing | Restore |
| Unreadable after retries | Refuse (§4.4) |
| Differs and is not a sealed entry: `root.json`, audit copy, table, `.torn`, orphan temporary file, snapshot file, disclosure record | Quarantine and restore. The commit is authoritative for unsealed files. |
| A sealed entry that fails to parse or seal | Quarantine and restore |
| A sealed entry that parses and seals but differs | Integrity failure (§1.3). Damage cannot produce a valid different seal. |
| An extra `NNNNNN.*` entry in a terminal-committed journal | Integrity failure (§1.3) |
| **Exception:** `000001.json` of a run committed only at consumption, when missing or damaged | Not restored. The attempt becomes `integrity_failure` (§9.4): later entries may also be lost, and continuing could repeat calls. Its protection is still evaluated file by file. |

**How a restore works.**
1. Move the damaged file to `D/quarantine/<token>/<relative path>`, with no replace, and flush the directory.
2. Write the committed bytes to `D/staging/`, flush them, and rename them into place with no replace and
   write-through. Flush the directory.

A kill at any point leaves the target either missing (restored again next time) or complete.
`D/staging/` is emptied by the lease holder. Restores are logged in `recovery.log`. Quarantined files are
committed at the next boundary, and they form the **restore log** that §12 discloses.

**Export.** The runbook requires these steps:
- a `git bundle` of `evidence.git` at the table freeze and at every Phase B terminal boundary;
- a copy of the table committed to `main` (§10.9);
- the evidence head, recorded in the Phase B terminal disclosure record. It is not in the `completed` receipt,
  so that receipt stays a pure derivation (J7).

## 14. Publication protocol

To publish `path` with content `bytes`:

1. Write the bytes to `dir/.tmp-<n>-<token>` and flush them (`FlushFileBuffers`, or `fsync` on POSIX).
2. Rename to `path` without replace:
   - **Windows:** `MoveFileExW(tmp, path, MOVEFILE_WRITE_THROUGH)` without `REPLACE_EXISTING`;
   - **POSIX:** `renameat2(RENAME_NOREPLACE)`, or `link` then `unlink`.
3. Flush the directory:
   - **Windows:** open it with `GENERIC_WRITE | FILE_FLAG_BACKUP_SEMANTICS` and call `FlushFileBuffers`;
   - **POSIX:** `fsync` it.

An entry is **published** when step 2 succeeds, and **durable** when step 3 then succeeds.

**Step 2 errors:**
- WinError 32 or 5 is retried up to 20 times at 100 ms intervals.
- `ERROR_ALREADY_EXISTS` / `EEXIST` is always a failure. Under the lease it means damage or tampering, and the
  command refuses.
- After any other error, the entry counts as published only if the temp is gone and `path` holds exactly the
  bytes. Otherwise it is not published, and the temp is left for §6.

**Step 3 errors:** the flush is retried up to 20 times. If it still fails, the entry is published but not
durable. The command then performs no irreversible action that depends on it, and exits.

Preflight checks that directory flush works on `D`'s volume. Projections use the same protocol, but replace
the old file.

## 15. The lease

`D/.lease` is opened **without truncation**, and one byte at offset 2^40 is locked exclusively and
non-blocking:
- **Windows:** `LockFileEx(LOCKFILE_EXCLUSIVE_LOCK | LOCKFILE_FAIL_IMMEDIATELY)`;
- **POSIX:** `fcntl(F_OFD_SETLK)`, or `flock` where OFD locks are unavailable.

**Holder information.** Only after locking does the holder rewrite the leading bytes with its token, process id,
host and start time. The locked byte lies beyond that text, so a refused command can read it and name the
holder.

**Release.** The OS releases the lock when the holder exits, crashes or is killed, and on reboot. There is no
staleness heuristic, no manual break, and no process-id check.

**Rules:**
- The lock handle is non-inheritable.
- Every child runs in the holder's kill-on-close job (§8). No child outlives the holder, and no child holds
  the lock.
- One lease covers both phases, both ledgers, every run, the table freeze and the evidence repository.
- Network volumes are refused at preflight.

## 16. Out of the journal

- **Telemetry and activity** (J10).
- **`recovery.log`:** restores, retries, removed git locks, and refusals including drift. No decision reads it.
- **Timestamps.**

## 17. Transport contract

Exactly one `POST /api/generate` per call. The adapter uses `max_retries=0` and follows no redirects. A test
uses a stub server that counts requests.

## 18. Write and crash table

| Write | After a kill or power loss at or just after it |
|---|---|
| Setup of `D.setup-*`, before the rename | No `D`; rerun sets up again and removes the leftover |
| Rename of `D.setup-*` to `D` | Either no `D` or a complete `D` |
| Lease lock | Released by the OS |
| `mkdir` of a run or journal | `absent` (R0); an orphan, or closed at ledger level (§6) |
| `run_created` (made durable before the ledger) | `created`, or an orphan if there is no ledger entry |
| `attempt_consumed` | Consumption boundary pending (§13.3) |
| Consumption commit | Pending until committed; no calls until then |
| `call_started` k, published but not durable | Not sent. `in_doubt(k)` closes it, or the entry never existed |
| `call_started` k, durable | `in_doubt(k)`, then closed |
| `call_recorded` k | Continue, close, or `awaiting_execution` |
| `execution_started` k | `execution_in_doubt`, then closed |
| Sandbox worker running | Killed with the job; `execution_in_doubt`, then closed |
| `execution_recorded` k | Continue or close |
| Record completing position N, with an interrupt pending | Exit without writing; `collected`; `--resume` scores |
| `scoring_started`, `scored`, `completed` | Next derived entry; a torn one is re-derived |
| Scorer running | Killed with the job; `scoring_interrupted`; `--resume` scores |
| `closed` | Terminal boundary pending, then the next attempt |
| Any boundary commit | Pending, completed by J8 step 5 |
| `hash-object`, `mktree`, `commit-tree` | Unreferenced objects; still pending |
| `update-ref` | Names the new commit (done) or the old one (pending) |
| Git child alive when the holder dies | Killed by the job; any `*.lock` it leaves is removed by the next holder |
| Rename to `.torn`; unlink of an identical pair | Replay identical before and after |
| A recovery publication after a tear, itself torn | The tear grows by one, with the same prediction |
| Temporary file deleted, or renamed to `.orphan-tmp-*` | Deleted only if identical; otherwise kept and named |
| Quarantine move during a restore | Target missing; the next command restores it |
| Staged restore rename | Target complete, or missing and restored next time |
| `ledger_torn_acknowledged` | One entry; the tail is still torn before it and closed after it |
| `attempt_closed_at_ledger` or a declaration, then its commit | Published, commit pending, completed by step 5 |
| Orphan snapshot commit, then folder move | Rerun `--clear-orphan`; idempotent |
| Table and audit copy published, then committed | An identical rerun does nothing. A torn table is rebuilt before its commit and restored after it. |
| Disclosure record | Part of its boundary commit, and rebuilt with it |
| Projection | Rebuilt |
| Interrupt flag set | Closed through the normal path before `collected`; plain exit after |

## 19. Verification

**Certification campaign (ruling 3).** It runs at freeze certification, and the freeze binds its report.

- **One choke point** for every filesystem write, every file read, and every child process.
- **Seeded scenarios:**
  - Normal runs and ordinary faults:
    - an uninterrupted synthetic run;
    - a transport failure, a sandbox failure, drift, abandon, clear-orphan and a declaration.
  - Torn and damaged entries:
    - a torn entry of every kind;
    - a torn entry after a failure record;
    - a torn recovery publication;
    - a torn ledger entry 1;
    - a torn ledger tail, with and without a committed copy, and with and without an orphan run claiming its
      head.
  - Durability and boundaries:
    - a directory flush that fails after the rename;
    - a pending consumption with a torn or absent `run_created`;
    - a kill during setup.
  - Committed-file damage:
    - a damaged or missing `root.json`;
    - a damaged committed entry, and a bit flip that still parses;
    - a changed committed entry that seals;
    - a kill during a restore.
  - Interrupts and children:
    - an interrupt at every safe point, including position N;
    - Ctrl+C during the sandbox;
    - a holder killed with live git, sandbox and scorer children.
  - Environment:
    - a git lock left behind;
    - a transient read error;
    - a second checkout, with `git gc` and `pack-refs` run in another checkout;
    - a new freeze after a completed or protected attempt.
- **Kills** after every operation and before every rename, then recursively during recovery, until a fixpoint.
- **Power loss** drops every unflushed operation and reorders unflushed renames. A separate **damage**
  injector truncates or corrupts any file.
- **Interference:**
  - sharing violations on reads and writes;
  - a second process racing for the lease;
  - a clock step while the lease is held.

**Oracles:**
- The end state is one of:
  - `completed`, with fact payloads equal to the uninterrupted run;
  - `closed` with a truthful reason, followed by a next attempt that completes;
  - a declared refusal (§1.3).
- J12: a stub provider counts calls per attempt and position, and every count is at most 1.
- No host-caused sandbox failure is recorded as a model failure.
- No temporary file is deleted unless it is identical to its entry.
- The disclosure is correct.
- Every committed item equals its copy on disk.
- No hand edit is ever needed.

**Other tests:**
- grammar-directed property tests for every §5 rule, and a mutation of every rule in §4.2;
- a transport test;
- a POSIX run of the protocol, lock and child-process tests.

**Normal suite.** A quick, representative, deterministic subset. It never touches the real `D`.

## 20. R6 contract clauses this design supersedes or carries

The following clauses of `QUALIFICATION_CONTRACT.md`, the launcher documentation, the freeze writer and the
freeze are replaced or carried. The replacements are reviewed with the implementation.

| R6 clause | R7 |
|---|---|
| Authorization consumed once the run exists and holds its lease | §9.2: lease, then durable `run_created`, then ledger, then consumption commit, then calls |
| A run is complete when the manifest reads `complete` and five terminal views agree | Replay state `completed` (§5) |
| Attempt and authorization fields in every record | `run_created` and the ledger |
| The launcher re-applies git anchors each command, as local commits on the branch | Boundary commits to the private evidence repository (§13) |
| `--abandon --reason <free text>`; a free-text orphan reason | Abandon on a failing preflight only (§9.3); automatic snapshots |
| A stale lease is removed by hand | An OS-held lock (§15) |
| Every non-complete end is anchored | Committed at its terminal or ledger-closure boundary, with a disclosure record |
| Ledger and run root agree | The ledger, orphan snapshots and closure snapshots (§9) |
| `source.phase_a_attempts` in the table | The §12 disclosure schema |
| The authorization sentences | §7.1 |
| A guarded digest in every record | Observed in every `call_started` |
| The table changing mid-run stops the run `incomplete` | Drift refuses until restored (§7) |
| The table committed, unmodified, in git on the branch | The table and audit copy in `D/tables/`, committed at the table freeze and verified by §13.4. A copy on `main` is checked by §10.9. |
| `authorization_ledger/` files in the checkout | A hash-chained ledger journal per phase in `D`, spanning freezes (§9.1) |
| Data under each checkout's `data/` | One fixed data root `D` for the experiment (§3) |
| The freeze writer refuses once a table exists | **Carried and extended** (§9.3): it refuses once `D` holds a table or a protected or completed attempt, and it refuses any other `D` |
| Coding execution runs in the runner's own process | An isolated worker in a kill-on-close job, shielded from console signals. Grading of a normal exit is unchanged (§8). |

## 21. Operator decisions and rulings

The rulings below are as the operator gave them. Where this design refines how a ruling is applied, the note is
marked *design note* and is not part of the ruling.

**2026-09-24**

1. One append-only journal per run is the authoritative history. Everything else is a projection.
2. A torn write or full-disk event closes the attempt rather than repeating the call.
3. The exhaustive crash harness runs at freeze certification; a quick representative suite runs in development.
4. Review happens in two stages: the design, then the implementation.
5. The partial drafts stay untracked and unwired until the design is accepted. Existing code does not decide
   the architecture.

**2026-09-25**

6. Torn `scored` and `completed` entries are re-derived byte-identically. A mismatch is an integrity failure,
   never a closure.
   - *Design note:* the payload is what is compared. Torn `scoring_started` entries are re-derived the same way
     (§5, §6).
7. `--abandon` is allowed only when the attempt is verified stuck. Partial cells and cross-attempt output
   identity are disclosed.
8. Evidence is committed to a dedicated git ref before every provider call. **This ruling is superseded by
   ruling 10.**
9. An integrity failure is recorded at ledger level, and the next attempt needs a distinct acknowledging
   sentence.

**2026-09-25, after design review round 2**

10. **Accidents in code, tampering at boundaries.**
    - The code guarantees at-most-once and a truthful history against accidents and against misuse of
      supported commands. Deliberate file edits are out of scope for the code.
    - At each attempt boundary and at the table freeze, the launcher commits that attempt's whole journal to
      git. The table freeze and Phase B verify it byte for byte.
    - Per-call git, high-water cross-checks and mid-run ref handling are dropped.
    - *Design note:* the git history lives in a private repository inside the fixed data root (§13), and every
      command verifies it, not only the table freeze and Phase B.

## 22. Out of scope: grading changes

The five grading issues from the R6 fixture review are a separate scientific change, with its own record and
review (`EXTERNAL_REVIEW_ROUND6.md`):
- dash and space normalization;
- a duplicate Answer line;
- a synthesis verbatim check;
- recursion and operators disclosure;
- a regex bound.

Provider generation calls for this design: **0**. Scientific runs launched: **0**.
