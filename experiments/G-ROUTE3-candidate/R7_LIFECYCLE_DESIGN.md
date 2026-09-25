# G-ROUTE3 R7 — journal/replay lifecycle architecture (design revision 4)

Status: **design-review candidate, revision 4.** Revisions 1 (`80a10d9`), 2 (`fd5c9f8`) and 3 (`df78fa0`) were
each reviewed by two independent reviewers and found not clean. Their findings, and the responses, are recorded
in `R7_DESIGN_REVIEW_ROUND1.md`, `R7_DESIGN_REVIEW_ROUND2.md` and `R7_DESIGN_REVIEW_ROUND3.md`.

Revision 4 makes two structural changes in response to round 3:
- **One fixed data root with a private evidence repository.** The data root is an absolute path outside every
  git checkout, bound in the execution freeze. The evidence repository lives inside it. So the evidence,
  ledgers, lease and runs are the same for every checkout, and no other worktree or tool can touch the
  evidence (§3, §13).
- **An OS-held lock.** The lease is a file lock held by the operating system and released when the process
  dies, so staleness is never guessed (§15).

It also makes every command verify **all** committed evidence before acting (§13.4), and settles the
torn-entry rules around failures and repeated tears (§5).

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

| | Guarantee |
|---|---|
| **G1** | **At most once.** No schedule position is sent to the provider twice within one attempt. |
| **G2** | **Truthful history.** Anything unproven is recorded as uncertain and disclosed, never guessed. |
| **G3** | **No best-of-N.** A completed attempt, or one whose collection finished, cannot be discarded or replaced. Every non-complete attempt is disclosed as one where optional stopping cannot be excluded. |
| **G4** | **A way forward.** Every reachable state has a supported command that leads to completion or to a recorded closure. The only exceptions are declared (§1.3), and each needs an operator ruling. |
| **G5** | **Determinism.** Replay is a pure function of a run's files. Derived entries re-derive to identical payloads. |

### 1.1 What the code defends against (operator ruling 10)

G1–G5 hold against **accidents** and **misuse of supported commands**. Accidents include:
- crashes, kills and power loss;
- a full disk, or a damaged file;
- sharing violations;
- `git clean`, `git stash` and `git gc` in any checkout;
- git lock files left behind.

**Tampering is caught at boundaries.** Each attempt's files are committed to the evidence repository at its
consumption boundary and its terminal boundary, and at the table freeze (§13). Every command, the table freeze
and Phase B included, verifies all committed files on disk against the evidence repository before it acts
(§13.4). So a change to anything committed is detected.

### 1.2 Declared residuals

These are trust assumptions, stated openly:

- **Tampering with an attempt in progress.** "In progress" means consumed with no committed terminal
  boundary. Deliberately editing, deleting or planting files of such an attempt is not prevented by the code.
  One example is deleting trailing journal files so that a call is sent again. Launch runs collection,
  scoring and completion in one process, and commits the terminal boundary before it returns, so this window
  is the attempt's own run time, plus any time after an interruption.
- **Antivirus deleting the trailing `call_started`.** An antivirus product that silently deletes the last
  journal file of a running attempt could cause a repeated call. `call_started` holds only digests, so this is
  implausible. The data root should be excluded from scanning; the runbook says so.
- **Out of scope, as before:** a fake model server, a second copy of the data root, rewriting the evidence
  repository's history, or deleting the whole data root.

### 1.3 Declared exceptions to G4

Each of these blocks the phase until an operator ruling:
- a persistent scorer defect (§6);
- an integrity failure of a protected attempt (§9.4);
- a committed file whose on-disk copy parses but differs, or an add-only conflict (§13.4);
- an evidence repository that is missing while ledger entries exist (§13.2).

## 2. Invariants

- **J1 — authority.** Each run has one append-only **journal**. Each phase has one append-only **ledger** of
  attempts (§9). Every other file is a projection, a committed copy, or a non-authoritative log.
- **J2 — sealed chain.** Every entry is sealed with its canonical digest (§4.4) and names the seal of the last
  valid entry before it (§4.1).
- **J3 — durable, non-overwriting publication.** Entries are published only by the §14 protocol. No
  irreversible action depends on an entry until that entry is **durable** (§14).
- **J4 — pure replay.** `replay(run files) → (state, observations)` is a pure, total function of the run's
  directory. It never writes and never reads git. Repairs are made only by `recover()` and the §13.4
  verification, and only by the lease holder.
- **J5 — facts only.** Entries hold facts. Nothing recomputable is stored.
- **J6 — always sealable.** Every value passes through `safe_value`. Raw model text is stored as base64 plus
  the sha256 of its text.
- **J7 — deterministic derivations.** Derived payloads (`scoring_started`, `scored`, `completed`) are pure
  functions of sealed inputs. Every re-derivation is compared by **payload**, only against sealed or
  committed data.
- **J8 — one command shape.** Every command runs these steps in order:
  1. take the lease (§15);
  2. verify committed evidence (§13.4);
  3. replay the ledgers and runs;
  4. recover to a fixpoint (§6), with the drift check before any step that derives an entry or runs the
     sandbox;
  5. complete pending boundary commits (§13.3);
  6. decide and act;
  7. commit any boundary the action reached, before returning.
- **J9 — way forward.** G4. §19 checks it mechanically.
- **J10 — inert telemetry.** Activity, telemetry and `recovery.log` are never read by any decision.
- **J11 — boundary evidence.** No `call_started` of an attempt is published before its consumption boundary
  is committed. A terminal entry's boundary is committed before the command that wrote it returns success.
  If that commit fails, the boundary stays pending, and step 5 of every later command completes it.
- **J12 — at most once.** A request is sent only after its `call_started` is durable. The next entry number
  is unique and publication never overwrites, so no second `call_started` for a position can exist. A started
  call whose outcome is not durably recorded closes the attempt. The call is never repeated.
- **J13 — nothing closes a finished collection.** Once every position is recorded and executed cleanly (the
  state `collected`), the only entries that may follow are `scoring_started`, `scored` and `completed`. From
  `collected` onward, drift and scorer failures make commands **refuse**; they never close.
- **J14 — zero transport retries.** Exactly one HTTP request is made per call (§17).

## 3. Files

The **data root** `D` is an absolute local path outside every git checkout. It is bound in the execution
freeze. The proposed path is `%LOCALAPPDATA%\Eidolon\research\g_route3`. Every checkout that runs under the
freeze uses the same `D`; a launcher whose freeze names a different `D` refuses. Preflight refuses a network
volume.

```
D/
  root.json                       created once: {"root_id": <random>, "freeze_binding": …}
  .lease                          the lease file; locked by the OS (§15)
  evidence.git/                   private bare git repository (§13)
  recovery.log                    non-authoritative
  tables/                         the qualification table and its audit document (§7)
  phase_a/, phase_b/
    ledger/NNNNNN.json | .torn    the attempt ledger (§9)
    runs/<run_id>/journal/NNNNNN.json | NNNNNN.torn | .tmp-* | .orphan-tmp-*
    runs/<run_id>/score.json, receipt.json      projections (§14)
    runs/.orphan-<run_id>-<token>/              cleared orphans (§9.4)
```

Replay considers only files named `NNNNNN.json` or `NNNNNN.torn`. Anything else is reported and ignored.

## 4. Journal entries

### 4.1 Envelope

```json
{"entry": n, "kind": "…", "run_id": "…", "previous_entry_sha256": "…",
 "acknowledges": [{"entry": m, "sha256": "…"}, …], "orphans": [{"name": "…", "sha256": "…"}, …],
 "payload": {…}, "record_sha256": "…"}
```

- **`previous_entry_sha256`** is the seal of the last **valid** entry before n, skipping `.torn` entries.
  - For a run's entry 1, it is the seal of the ledger head that `run_created` claims to follow.
  - For a ledger's entry 1, it is the **genesis seal**, the canonical digest of
    `{"genesis": "g-route3-ledger", "phase": "A" | "B", "root_id": …}`.
- **`acknowledges`** lists every `.torn` entry between the last valid entry and n, with the sha256 of its
  bytes. It is empty otherwise.
- **`orphans`** names every `.orphan-tmp-*` file in the directory not yet named by an earlier entry (§6).

Both lists are in the envelope, so a derived entry's payload stays equal to its re-derivation. There is no
timestamp in any seal. Times appear only in `recovery.log` and in git commits.

### 4.2 Kinds

| Kind | Payload | May follow (the last valid entry) |
|---|---|---|
| `run_created` | Phase, attempt number, authorization digest, the sentence's sha256, claimed ledger head; schedule, guarded and freeze digests; `root_id`; synthetic flag; fixed endpoint; model receipts; transport contract; for Phase B, the table digest, the Phase A run id, and the evidence commit id bound into the table | Nothing: it is entry 1 |
| `call_started` | Position k, call id, request digest, the guarded digest observed now | `run_created` (k = 1); a clean non-coding `call_recorded` k−1; a clean `execution_recorded` k−1 |
| `call_recorded` | Position k, equal to the preceding `call_started`. Provider raw body (base64) and its sha256; raw output (base64) and the sha256 of its text; returned model; scalar metrics; `transport_failure`, which is empty unless the provider boundary raised | `call_started` k |
| `execution_started` | Position k, candidate digest | A clean coding `call_recorded` k |
| `execution_recorded` | Position k, sandbox evidence, candidate error, `infrastructure_failure` | `execution_started` k |
| `scoring_started` | Digest of the fact prefix; for Phase B, the seals of the disclosure inputs (the ledger head, and every earlier attempt's terminal entry) | `collected` |
| `scored` | The score report: a pure function of the inputs named in `scoring_started` (§4.3) | `scoring_started` |
| `completed` | Receipt: chain head seal, `scored` seal, `run_created` seal, freeze and guarded digests | `scored` |
| `closed` | A reason from the list below; `calls_started`, `calls_recorded`, `executions_started`; the in-doubt position if any; the exception class and message if any | Any entry from `run_created` up to, but not including, `collected`. Never after `collected` (J13). |

**`closed` reasons:**

| Reason | Cause |
|---|---|
| `transport_failure` | A failure field on the last `call_recorded` |
| `infrastructure_failure` | A failure field on the last `execution_recorded` |
| `execution_interrupted` | An `execution_started` with no record |
| `call_outcome_unknown` | A `call_started` with no record |
| `durability_uncertain` | A torn entry whose content cannot be re-derived |
| `operator_interrupt` | SIGINT, SIGTERM or CTRL_BREAK (§7) |
| `abandoned_preflight_failed:<checks>` | `--abandon` (§9.3) |

Every one of them is disclosed with the flag "optional stopping cannot be excluded" (§12).

A failure field, an unrecorded call, or an interrupted execution means the next entry is `closed`. A call is
never retried.

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

## 5. Replay: an ordered, total decision procedure

**Inputs.** The entries are the `NNNNNN.json` and `NNNNNN.torn` files. An `n.json` whose bytes equal an existing
`n.torn` is treated as that `.torn` alone; recovery unlinks the `.json`. That pair is what a POSIX rename
interrupted between link and unlink leaves behind.

**Terms.**
- The **trailing tear** is the maximal run of `.torn` entries at the highest numbers.
- The **last valid entry** is the highest-numbered entry that parses and seals.

Rules apply **in order; the first match wins**:

| # | Condition | State |
|---|---|---|
| R0 | No `journal/` directory, or no `.json` and no `.torn` entries in it | `absent` |
| R1 | The numbers 1 … highest are not each occupied by exactly one entry. Or an `n.json` and an `n.torn` have different bytes. | `integrity_failure` |
| R2 | A `.json` other than the highest-numbered fails to parse or seal | `integrity_failure` |
| R3 | A sealed entry fails a grammar or payload check (below) | `integrity_failure` |
| R4 | A `.torn` outside the trailing tear is not listed in the next valid entry's `acknowledges`. Or, in a run journal, entry 1 is `.torn` and any valid entry exists. | `integrity_failure` |
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
| R16 | The last entry is a clean record of k, where k is less than N | `collecting(k)` |
| R17 | The last entry is `run_created` | `created` |

**Grammar and payload checks (R3)** apply to every sealed entry, **including the last**:
- the entry number equals the file name, and the run id is constant;
- `previous_entry_sha256` names the last valid entry before it, and `acknowledges` lists exactly the `.torn`
  entries in between, with their sha256;
- `orphans` names only files that exist, each once across the journal;
- the kind follows §4.2;
- positions and call ids match the schedule;
- nothing follows `completed` or `closed`;
- `closed` never follows `collected`;
- only `closed` follows a failure field;
- the `completed` receipt matches the chain.

**Predicting a trailing tear** (R6). The prediction comes from the last valid entry and the fact prefix. Every
`.torn` in the tear gets the same prediction, because none of them was recorded.

| Last valid entry | Predicted kind | Class |
|---|---|---|
| None (the tear starts at entry 1) | `run_created` | special (§6) |
| `run_created`, or a clean record of k less than N | `call_started` | provider |
| `call_started` k | `call_recorded` | provider |
| A clean coding `call_recorded` k | `execution_started` | provider |
| `execution_started` k | `execution_recorded` | provider |
| A record carrying a failure field | `closed` (with that failure's reason) | closure |
| A clean record completing position N (`collected`) | `scoring_started` | derived |
| `scoring_started` | `scored` | derived |
| `scored` | `completed` | derived |
| `completed` or `closed` | Nothing may follow. Nothing is ever written after a terminal entry, so a tear here comes only from damage or tampering: the state is `integrity_failure`, and §13.4 applies once the terminal boundary is committed. | — |

Torn bytes are never parsed for decisions.

## 6. `recover()`: one step at a time, by the lease holder

Every recovery rename, unlink or deletion is followed by a directory flush before the next step.

**Drift first.** Before any step that derives an entry or runs the sandbox, the guarded digest is compared
with the one in `run_created`. If it differs, the command refuses and names the drifted paths and digests.

| State | Recovery step |
|---|---|
| `torn_tail(n)` | Rename `n.json` to `n.torn` without replace. If an identical `n.torn` already exists, unlink `n.json` instead. Then replay again. |
| `torn_pending(T, provider)` | Publish `closed(durability_uncertain)` after the tear, acknowledging T |
| `torn_pending(T, closure)` | Publish `closed(<the failure's reason>)` after the tear, acknowledging T |
| `torn_pending(T, derived)` | Drift check, then re-derive the entry and publish it after the tear, acknowledging T. If a committed copy of that kind exists, the payloads must be equal; a mismatch is an integrity failure. |
| `torn_pending(T from 1, run_created)` | No call can have been made, because no valid entry exists. If no ledger entry names this run, it is an orphan (§9.4). If the attempt's consumption boundary is **not** committed, publish `attempt_closed_at_ledger(durability_uncertain)` with a snapshot (§9.1). If it **is** committed, the state is `integrity_failure` (§9.4). |
| `in_doubt(k)` | Publish `closed(call_outcome_unknown, in_doubt=k)` |
| `execution_in_doubt(k)` | Publish `execution_recorded(k, infrastructure_failure=execution_interrupted)`. The sandbox is never re-run, and the provider output is kept. `faulted` then closes the attempt. |
| `faulted(k)` | Publish `closed(<the failure's reason>)` |
| `awaiting_execution(k)` | Drift check, then collection continues (§8 step 5) |
| `scoring_interrupted` | Drift check, then run the scorer in a subprocess with a timeout. On success, publish `scored`. **On failure, refuse** (J13). The scorer is provider-free and deterministic, so a persistent failure is a defect (§1.3). |

**Temporary files.**
- A `.tmp-*` whose bytes equal the entry published at its number is deleted.
- Any other `.tmp-*` is renamed to `.orphan-tmp-<n>-<token>`. The next entry published in that directory
  names it in `orphans`. If the directory is terminal, the name is carried by the terminal boundary commit
  instead. Orphan temps are committed with the journal, and no provider output is ever deleted.

## 7. Commands

Every command follows J8. In the table, "sentence" means the exact operator sentence in §7.1.

| State after recovery | launch n | `--resume` n | `--abandon` n | `--declare-integrity-failure` n |
|---|---|---|---|---|
| No run, attempt n not consumed | Allowed when §9.3 holds: publish `run_created`, then `attempt_consumed`, then commit the consumption boundary, then collect, score and complete | refused | refused | refused |
| `created`, `collecting`, `awaiting_execution` | refused | collect | allowed only on a failing preflight (§9.3) | refused |
| `collected`, `scored` | refused | score and complete | refused | refused |
| `completed` | refused | re-project only | refused | **refused** (§9.4) |
| `closed`, or closed at ledger level | the next attempt | refused | refused | refused |
| `integrity_failure`, or `absent` with attempt n consumed | refused | refused | refused | allowed unless protected (§9.4) |
| A run folder without a ledger entry | refused | refused | refused | refused (`--clear-orphan` instead) |

- **Drift in `created`, `collecting` or `awaiting_execution`.** The command refuses until the guarded files are
  restored, and names the paths and digests. It does not close anything.
- **Interrupts.** The handler for SIGINT, SIGTERM and CTRL_BREAK only sets a flag. The main loop checks the
  flag before each `call_started`, and after each record. If the flag is set, it publishes
  `closed(operator_interrupt)` through the normal path and exits. A request already in flight is completed
  and recorded first. A second signal, or a hard kill, leaves the state for the next command to classify.
- **Attempt numbers.** A launch's n must equal the number of consumed attempts plus 1. `--resume n` requires n
  to be the latest consumed attempt, and is refused if a later attempt exists. The run id always comes from
  the ledger entry.
- **`--freeze-table`** runs, after J8 steps 1–5, which already verify every committed attempt and both
  ledgers:
  - it requires the named Phase A attempt to be `completed` with its terminal boundary committed, every other
    Phase A attempt to be closed or closed at ledger level, and no Phase A attempt to be in progress;
  - it builds the table deterministically from the replayed `scored` entry. The table records the attempt's
    run id, its `run_created` and `scored` seals, and the evidence commit id of its terminal boundary;
  - the audit document must read `READY`, name both seals, and not be a frozen artifact. Its bytes are copied
    to `D/tables/` and bound into the table by sha256;
  - the table and the audit copy are published with §14 without replace, then committed in the table-freeze
    commit;
  - a rerun that finds the identical table does nothing. A parseable, different table is refused.
- **`--clear-orphan`** is described in §9.4.

### 7.1 Sentences

Each sentence is matched as a full string. `<binding>` must equal the execution-freeze digest in force, and
`<table>` must equal the frozen table's digest. `<P>` is `A` or `B`. Numbers have no leading zeros.

| Command | Sentence |
|---|---|
| Launch, Phase A | `Authorize G-ROUTE3 phase A execution <binding> attempt <n>` |
| Launch, Phase B | `Authorize G-ROUTE3 phase B execution <binding> table <table> attempt <n>` |
| Launch after a ledger-level integrity closure (§9.4) | Either launch form, followed by ` after integrity failure of attempt <n-1>` |
| `--resume n` | Byte-identical to the sentence consumed for attempt n. It consumes nothing. |
| `--abandon n` | `Abandon G-ROUTE3 phase <P> attempt <n> after failed preflight` |
| `--declare-integrity-failure n` | `Declare G-ROUTE3 phase <P> attempt <n> integrity failure` |
| `--clear-orphan` | `Clear G-ROUTE3 phase <P> orphan run <run_id>` |
| `--freeze-table` | `Freeze G-ROUTE3 qualification table from phase A attempt <n> of execution <binding>` |

**Which launch form applies.** The distinct form is required exactly when attempt n−1 was closed at ledger
level as `integrity_failure` or `journal_missing`. The ordinary form is refused then, and the distinct form is
refused otherwise. Only launch sentences authorize provider contact. Each operator sentence is Marcus's to
give; none is ever self-issued.

## 8. One call

1. Check the guard.
2. Publish `call_started` k and wait until it is **durable** (§14). If it cannot be made durable, exit
   without sending. The next command finds `in_doubt(k)` and closes the attempt.
3. Send exactly one request (J14).
4. Publish `call_recorded` k, with `transport_failure` set if the provider boundary raised.
5. For a coding call:
   - publish `execution_started` k and wait until it is durable;
   - run the sandbox once;
   - publish `execution_recorded` k.
6. If a failure field is set, publish `closed`.

No git operation happens inside the per-call loop.

## 9. Attempts: the ledger

### 9.1 Ledger entries

Each phase's ledger is a hash-chained journal in `D/phase_X/ledger/`. It uses the same envelope, protocol,
torn and temporary-file handling, and rules R0–R6 as a run journal. It starts from the genesis seal, and the
entry-1 clause of R4 does not apply to it. It has three kinds:

- **`attempt_consumed`:** attempt number, the verbatim sentence, authorization digest, run id, and the
  `run_created` seal.
- **`attempt_closed_at_ledger`:** attempt number and reason (`integrity_failure`, `journal_missing` or
  `durability_uncertain`); what was observed; counts marked **unknown**, with lower bounds taken from any
  committed copy; and the path of the **closure snapshot**. That snapshot is the run folder's files as found,
  committed under `closures/<phase>/<attempt>/` (§13.1).
- **`ledger_torn_acknowledged`:** one entry that acknowledges a torn ledger tail and, if the torn entry was an
  uncommitted `attempt_consumed`, also closes that attempt as `durability_uncertain`. No call can have been
  made, because J11 requires the consumption commit first.

**A torn or missing ledger entry that has a committed copy** is restored byte for byte by §13.4, never
acknowledged. The committed copy wins. `ledger_torn_acknowledged` is used only for a tail that was never
committed.

### 9.2 Order at launch

1. Take the lease.
2. Publish `run_created`, whose previous seal is the ledger head it claims.
3. Publish `attempt_consumed`, naming the `run_created` seal.
4. Commit the **consumption boundary**: the ledger entry and `000001.json` (§13).
5. Collect, score and complete in the same process, then commit the terminal boundary.

**What an interruption leaves.**
- **Between 2 and 3:** an orphan with no calls.
- **Between 3 and 4:** a consumed attempt with its boundary pending. J8 step 5 commits it if the run replays
  to `created`. Otherwise §6 closes it at ledger level; no call was possible.

### 9.3 Attempt policy

- **Launch.** Attempt n+1 may be launched only when every earlier attempt of the phase is `closed` or closed
  at ledger level. Launch is refused if any earlier attempt replays as `completed`, or has a committed
  `completed` copy. The first `completed` attempt is the result.
- **Abandon.** `--abandon` is allowed only when the command's own preflight fails with a **persistent**
  condition: the model receipts differ from the frozen bindings, or the freeze no longer verifies. An
  unreachable provider or a transient error is not a preflight failure; `--resume` handles it through the
  normal paths. Drift is not a preflight failure either, because it refuses until the files are restored.
  The closure names the failing checks.
- **Optional stopping.** It cannot be prevented mechanically, so it is disclosed (§12).

### 9.4 Integrity failures, missing journals, orphans

**Ledger-level closures.** A declared closure is published by `--declare-integrity-failure`. An automatic one
is published by §6 or §9.1, and only when no call was possible. Both kinds commit a closure snapshot. The
**protection rules** apply to every ledger-level closure, declared or automatic: it is **refused** when
- the attempt has a committed terminal copy; or
- any sealed entry on disk in its journal is `scoring_started`, `scored` or `completed`, or its valid prefix
  reaches `collected`; or
- it is the Phase A attempt a frozen table names.

A refusal blocks the phase until an operator ruling. So a finished collection cannot be discarded by damaging
its files.

**`--clear-orphan`** accepts only a run folder that has no `call_started` and no ledger entry. It commits an
orphan snapshot under `orphans/<phase>/<run_id>/`. It then moves the folder to `runs/.orphan-<run_id>-<token>`
with a no-replace directory rename: `MoveFileExW` without replace, or on POSIX `renameat2(RENAME_NOREPLACE)`
or else `mkdir` plus per-file no-replace moves. A rerun is idempotent. Orphans are disclosed.

## 10. Phase B preconditions

Phase B may contact the provider only when all of these hold (J8 step 2 has already verified every committed
file):

1. The named Phase A attempt replays as `completed`, with its terminal boundary committed.
2. It is the only completed Phase A attempt. Every other Phase A attempt is closed or closed at ledger level,
   and none is in progress.
3. Its `run_created` attempt, authorization digest and sentence digest equal its ledger entry, and the ledger
   entry names the `run_created` seal.
4. It is not synthetic and it ran under this freeze. Its guarded digest, in `run_created` and in every
   `call_started`, equals today's. Its model receipts verify, and its endpoint is the fixed one.
5. The provider evidence of every call is consistent: body digest, model, output, and request digest, each
   checked against the schedule.
6. Cells re-derived from its facts equal both its `scored` cells and the table's cells.
7. **Table checks.** Every R6 table check is carried over, and three are added.
   - Carried over from R6:
     - the table's digest recomputes;
     - the routing lookup is exactly what the cells imply;
     - the table was derived from Corpus A alone (`corpus_b_consulted` false);
     - its corpus, gold and threshold digests match;
     - it is bound to this freeze;
     - its audit reads `READY`, is not a frozen artifact, and its document sha256 matches the committed audit
       copy.
   - Added in R7:
     - the table's run id and seals equal the named attempt's;
     - the table and its audit copy on disk equal their table-freeze commit;
     - the table names the evidence commit holding the attempt's terminal copy.
8. The table's attempt disclosure equals the disclosure computed now (§12).
9. The Phase B sentence names the freeze, the table and attempt n, and is consumed through §9.
10. `D/tables/<table>` is inside Phase B's per-call guard.

## 11. Durability

- **G1 needs no git.** It rests on `call_started` being durable before the request (§14), and on the unique
  next entry number.
- **Every journal and ledger entry is durable before any irreversible step that depends on it.** Irreversible
  steps are a request, the sandbox, and a boundary commit that names the entry.
- **Boundary commits are durable before a command reports success.** The evidence repository's own config
  sets `core.fsync=all` and `core.fsyncMethod=fsync`. Git 2.38 or later is required, and preflight checks the
  version. The ref directory is flushed after `update-ref`. The repository has no other worktrees and no
  automatic gc, so no other process ever rewrites its refs.
- **Accidental losses are recorded, never guessed.** An in-doubt call closes the attempt. A torn entry stays
  in place. An unmatched temp file is kept under a unique name. A damaged committed file is restored from its
  commit.

## 12. Disclosure

The qualification table and the Phase B score disclose the following for every attempt of the phase,
including ledger-level closures and cleared orphans:

- attempt number, run id, outcome, and closure reason;
- the flag **"optional stopping cannot be excluded"** on every non-complete attempt;
- `calls_started`, `calls_recorded` and `executions_started`, and the in-doubt position if any. For a
  ledger-level closure, these are **unknown**, with lower bounds;
- **partial results:**
  - for Phase A, the cells re-derived from the attempt's recorded calls;
  - for Phase B, the per-observation correctness of its recorded calls, and the routing decisions it could
    determine;
- for every seeded position recorded in more than one attempt, whether the raw-output sha256 values are
  identical. Where an attempt's journal is unavailable, this is marked **undeterminable**;
- the evidence commit id of each boundary.

## 13. The evidence repository

### 13.1 Layout and commits

`D/evidence.git` is a private bare repository. The first launch creates it before the first ledger entry,
with this config:
- `core.fsync=all` and `core.fsyncMethod=fsync`;
- `gc.auto=0`;
- `core.logAllRefUpdates=always`.

Its one ref is `refs/heads/evidence`, with a linear history. Every commit's tree holds `root.json`, and a
commit whose `root_id` differs from `D/root.json` is refused.

The tree layout is:

```
root.json
phase_{a,b}/ledger/NNNNNN.json | .torn
phase_{a,b}/runs/<run_id>/journal/<file>      every file in the journal directory
closures/<phase>/<attempt>/<file>             closure snapshots
orphans/<phase>/<run_id>/<file>               orphan snapshots
tables/<table file>, tables/<audit copy>
```

There are five kinds of boundary commit:

| Boundary | When | Adds |
|---|---|---|
| **Consumption** | After `attempt_consumed`, before any `call_started` | The ledger entry and `000001.json` |
| **Terminal** | After `completed` or `closed` | New ledger entries, and every file in the run's `journal/` |
| **Ledger closure** | After any ledger-level closure | The ledger entry and the closure snapshot |
| **Orphan** | Before an orphan folder is moved | The orphan snapshot |
| **Table freeze** | After the table is published | The table and the audit copy |

A commit's content comes only from a replay that reached the boundary's state, or, for a snapshot, from the
files as found. Commits use plumbing with a private index: `hash-object -w`, `mktree`, `commit-tree`, then
`update-ref <ref> <new> <expected-old>`.

### 13.2 Rules

- **Add-only.** A commit may only add paths. If a path already exists with different bytes, the command
  refuses (§1.3).
- **Never recreated.** If `evidence.git` or its ref is missing while any ledger entry exists, the command
  refuses (§1.3).
- **Unreadable.** If the repository cannot be read, the command refuses. An unreadable repository is never
  treated as empty.
- **Locks.** Only the lease holder runs git in `evidence.git`. So any `*.lock` file found there by the lease
  holder was left by a killed git process. It is removed and logged.
- **Retries.** If `update-ref` reports failure, the ref is re-read. If it already names the new commit, the
  commit succeeded. Otherwise the commit is retried up to 5 times, then left pending.

### 13.3 Pending boundaries

A boundary is **pending** when a replayed state requires a commit that the ref does not yet hold. Pending
boundaries are computed from replay (J8 step 5), not from `recovery.log`.
- A pending consumption boundary blocks all calls of that attempt.
- A pending terminal boundary blocks the next launch, the table freeze and Phase B.
- If a consumption boundary is pending and the run cannot replay to `created`, the boundary is superseded by
  the §6 ledger-level closure.

### 13.4 Verification (every command, J8 step 2)

Every committed file is compared with its copy on disk:

| Committed item | Missing, or unparseable on disk | Parses but differs, or extra files on disk |
|---|---|---|
| Ledger entries | The damaged file is renamed `.damaged-<token>`, then the committed bytes are restored with §14 | Integrity failure (§1.3). Ledger entries beyond the committed ones are normal. |
| Journal of a terminal-committed run | Restored the same way | Integrity failure (§1.3) |
| `000001.json` of a run committed only at consumption | Not restored: the attempt becomes `integrity_failure` (§9.4), because later entries may also be lost | Integrity failure |
| Closure snapshot, table, audit copy | Restored | Integrity failure (§1.3) |

Restores are logged, and disclosed in §12.

**Export.** Reviewers get the repository as a `git bundle`. The terminal evidence commit ids are bound into
the table. The operator commits a copy of the table to `main` after the freeze, which ties the private
evidence to the public history.

## 14. Publication protocol

To publish `path` with content `bytes`:

1. Write the bytes to `dir/.tmp-<n>-<token>`, then flush (`FlushFileBuffers`, or `fsync` on POSIX).
2. Rename the temp to `path`, with no replace:
   - **Windows:** `MoveFileExW(tmp, path, MOVEFILE_WRITE_THROUGH)` without `REPLACE_EXISTING`;
   - **POSIX:** `renameat2(RENAME_NOREPLACE)`, or else `link` then `unlink`.
3. Flush the directory:
   - **Windows:** open it with `GENERIC_WRITE | FILE_FLAG_BACKUP_SEMANTICS` and call `FlushFileBuffers`;
   - **POSIX:** `fsync` the directory.

The entry is **published** when step 2 succeeds, and **durable** when step 3 then succeeds.

**Errors in step 2.**
- A sharing violation (WinError 32) or access denied (WinError 5) is retried up to 20 times at 100 ms
  intervals.
- **`ERROR_ALREADY_EXISTS` / `EEXIST` is always a failure.** Under the lease, it can only mean damage or
  tampering, so the command refuses.
- After any other error, the entry counts as published only if the temp is gone and `path` holds exactly
  these bytes. Otherwise it is not published, and the temp is left for §6.

**Errors in step 3.** The directory flush is retried up to 20 times. If it still fails, the entry is published
but not durable. The command performs no irreversible action that depends on it, and exits.

The lease is never lost while the process lives (§15), so no second writer exists. Preflight checks that
directory flush works on `D`'s volume. Projections use the same protocol but replace the old file.

## 15. The lease

`D/.lease` is opened and locked with an exclusive, non-blocking OS lock:
- **Windows:** `LockFileEx(LOCKFILE_EXCLUSIVE_LOCK | LOCKFILE_FAIL_IMMEDIATELY)`;
- **POSIX:** `fcntl(F_SETLK)`.

The process holds the lock for its whole life. The operating system releases it when the process exits,
crashes or is killed, and on reboot. A second command that cannot take the lock refuses and names the holder,
using the informational content the holder writes into the file: token, process id, host and start time.

- The lock handle is non-inheritable, so a sandbox child can never hold the lease.
- One lease covers both phases, both ledgers, every run, the table freeze and the evidence repository. This
  matches "one local-model research job at a time".
- There is no staleness heuristic, no manual lease break, and no process-id check.
- Network volumes are refused at preflight, because their locks are unreliable.

## 16. Out of the journal

- **Telemetry and activity** (J10).
- **`recovery.log`.** It records restores, retries, removed git locks, and refusals, including drift. No
  decision reads it.
- **Timestamps.**

## 17. Transport contract

Exactly one `POST /api/generate` per call. The adapter uses `max_retries=0` and follows no redirects. A test
uses a stub server that counts requests.

## 18. Write and crash table

| Write | After a kill or power loss at or just after it |
|---|---|
| `D`, `root.json`, `evidence.git` creation | Rerun creates what is missing. A missing repository is refused only once ledger entries exist. |
| `mkdir` of a run or journal | `absent` (R0). Launch continues, or the folder becomes an orphan. |
| Lease file | Released by the OS |
| `run_created` | `created`, or an orphan if there is no ledger entry |
| `attempt_consumed` | Consumption boundary pending (§13.3) |
| Consumption commit | Pending until committed; no calls until then |
| `call_started` k, published but not durable | Not sent. `in_doubt(k)` closes, or, if the rename was lost, the entry never existed. |
| `call_started` k, durable | `in_doubt(k)`, then closed |
| `call_recorded` k | Continue, close, or `awaiting_execution` |
| `execution_started` k | `execution_in_doubt`, then closed |
| `execution_recorded` k | Continue or close |
| `scoring_started`, `scored`, `completed` | The next derived entry. A torn one is re-derived. |
| `closed` | Terminal boundary pending, then the next attempt |
| Terminal, ledger-closure, orphan or table-freeze commit | Pending, completed by step 5 of the next command |
| `hash-object`, `mktree`, `commit-tree` | Unreferenced objects; the boundary is still pending |
| `update-ref` | The ref names either the new commit (done) or the old one (pending) |
| A git lock left in `evidence.git` | Removed by the next lease holder |
| Rename to `.torn`; unlink of an identical pair | Replay is the same before and after. Idempotent. |
| Recovery publication after a tear, itself torn | The tear grows by one, with the same prediction |
| Temp deletion, or rename to `.orphan-tmp-*` | Deleted only if identical, otherwise kept and named by the next entry |
| Restore of a committed file (§13.4) | Rerun restores it; `.damaged-*` files are kept |
| `ledger_torn_acknowledged` | One entry. Before it, the tail is still torn; after it, closed. |
| `attempt_closed_at_ledger`, then its commit | The closure is published and its commit pending; completed by step 5 |
| `--declare-integrity-failure` | Same as the line above |
| Orphan snapshot commit, then folder move | Rerun `--clear-orphan`; idempotent |
| Table and audit copy publish, then commit | An identical rerun does nothing. A torn table is rebuilt identically before its commit, and restored after it. |
| Projection | Rebuilt |
| Interrupt flag set | The main loop closes through the normal path |

## 19. Verification

**Certification campaign (ruling 3).** It runs at freeze certification, and the freeze binds its report.

- **One choke point** for every filesystem write and every git call.
- **Seeded scenarios:**
  - an uninterrupted synthetic run;
  - a transport failure, a sandbox failure, drift, abandon, clear-orphan and a declaration;
  - a torn entry of every kind, including a torn entry after a failure record and a torn recovery
    publication;
  - a torn ledger entry 1, and a torn ledger tail with and without a committed copy;
  - a directory flush that fails after the rename;
  - a pending consumption boundary with a torn `run_created`;
  - a git lock left behind;
  - a damaged committed file, and a changed committed file;
  - a second checkout using the same `D`, with `git gc` and `pack-refs` run in another checkout.
- **Kills** after every operation and before every rename, then again during recovery, repeated to a fixpoint.
- **Power loss.** It drops every operation not yet flushed and reorders renames that were not flushed. A
  separate **damage** injector truncates or corrupts any file, because a torn entry needs a device fault.
- **Interference:**
  - sharing violations;
  - a second process racing for the lease;
  - a clock step while the lease is held, which must make no difference.

**Oracles:**
- the end state is `completed`, with fact payloads equal to those of the uninterrupted run; or `closed` with a
  truthful reason, followed by a next attempt that completes; or a declared refusal (§1.3);
- J12: a stub provider counts calls per attempt and position, and every count is at most 1;
- no temp file is deleted unless it is identical to its entry;
- the disclosure is correct;
- every committed item equals its copy on disk;
- no hand edit is ever needed.

**Other tests:**
- grammar-directed property tests covering every §5 rule, and a mutation of every rule in §4.2;
- a transport test;
- a POSIX run of the protocol and lock tests.

**Normal suite.** A quick, representative, deterministic subset of all of the above. It never touches the real
`D`.

## 20. R6 contract clauses this design supersedes

These clauses in `QUALIFICATION_CONTRACT.md`, the launcher documentation and the freeze are replaced. The
replacements are reviewed with the implementation.

| R6 clause | Replacement |
|---|---|
| Authorization consumed once the run exists and holds its lease | §9.2: lease, then `run_created`, then the ledger, then the consumption commit, then calls |
| A run is complete when its manifest reads `complete` and five terminal views agree | Replay state `completed` (§5) |
| Attempt and authorization fields in every record | `run_created` and the ledger |
| The launcher re-applies git anchors on every command, as local commits on the branch | Boundary commits to the private evidence repository (§13) |
| `--abandon --reason <free text>`, and a free-text orphan reason | Abandon on a failing preflight only (§9.3), and automatic snapshots |
| A stale lease is removed by hand | An OS-held lock (§15) |
| Every non-complete end is anchored | Committed at its terminal or ledger-closure boundary |
| The ledger agrees with the run root | The ledger, orphan snapshots and closure snapshots (§9) |
| `source.phase_a_attempts` in the table | The §12 disclosure schema, with evidence commit ids |
| The authorization sentences | The table of sentences in §7.1 |
| A guarded digest in every record | Observed in every `call_started` |
| The table changing mid-run stops the run as `incomplete` | Drift refuses until the files are restored (§7) |
| The table is committed, unmodified, in git on the branch | The table and audit copy in `D/tables/`, committed at the table freeze and verified by §13.4. A copy goes to `main`. |
| `authorization_ledger/` files in the checkout | A hash-chained ledger journal per phase in `D` (§9.1) |
| Data under each checkout's `data/` | One fixed data root `D`, bound in the freeze (§3) |

## 21. Operator decisions and rulings

**2026-09-24**

1. One append-only journal per run is the authoritative history. Everything else is a projection.
2. A torn write or full-disk event closes the attempt instead of repeating the call.
3. The exhaustive crash harness runs at freeze certification, and a quick representative suite runs in
   development.
4. Review happens in two stages: the design, then the implementation.
5. The partial drafts stay untracked and unwired until the design is accepted. Existing code does not decide
   the architecture.

**2026-09-25**

6. Torn `scored` or `completed` entries are re-derived byte for byte. A mismatch is an integrity failure,
   never a closure. Revisions 3 and 4 make this precise: the payload is compared, and torn `scoring_started`
   is re-derived the same way.
7. `--abandon` is allowed only when the attempt is verified stuck. Partial results and cross-attempt output
   comparisons are disclosed.
8. *Superseded by ruling 10.* It had required evidence committed before every provider call.
9. An integrity failure is recorded at ledger level, and the next attempt needs a distinct sentence. It is
   refused for protected attempts (§9.4).

**2026-09-25, after design review round 2**

10. **Accidents are handled in code; tampering is caught at boundaries.** The code guarantees G1–G5 against
    accidents and misuse of supported commands. Deliberate file edits between boundaries are out of scope for
    the code. At every attempt boundary and at the table freeze, the launcher commits the attempt's journal to
    git. The table freeze and Phase B verify it byte for byte. Per-call git evidence, high-water cross-checks
    and mid-run ref handling are removed. Revision 4 places that git history in a private repository inside
    the fixed data root, and verifies it on every command.

## 22. Out of scope: grading changes

The five grading issues from the R6 fixture review are a separate scientific change. It gets its own record
and review; see `EXTERNAL_REVIEW_ROUND6.md`. The issues are:
- dash and space normalization;
- a duplicate Answer line;
- a synthesis verbatim check;
- recursion and operator disclosure;
- a regex bound.

Provider generation calls for this design: **0**. Scientific runs launched: **0**.
