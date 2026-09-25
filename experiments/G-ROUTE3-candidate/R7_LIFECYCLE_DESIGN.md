# G-ROUTE3 R7 — journal/replay lifecycle architecture

Status: **design-review candidate.** Operator decisions of 2026-09-24 are incorporated (§12). This document is
bound by digest in `R7_DESIGN_REVIEW_CANDIDATE.json`. No implementation is wired in, no execution freeze is
written, no provider is contacted, and no scientific run is launched. R6 (`2e5e8cc7…`) stays frozen,
unauthorized and void.

**Review sequence.**
1. Design review now: two fresh read-only reviewers.
2. If the design review is clean, implement R7 from this document.
3. Review the implementation, with fresh reviewers and the certification crash campaign.
4. Only then offer an R7 execution freeze for authorization.

Scope: how a G-ROUTE3 run records what happened and recovers from interruption. That covers run creation,
authorization binding, collection, closure, finalization, projections, git anchoring, attempts, and the
launcher commands built on them. The scientific design is **unchanged** and out of scope here: corpora, gold,
validators, the qualification rule, routing, gates and thresholds.

## 1. Why a redesign

Six external reviews found blocking lifecycle defects in every round from R2 to R6. The individual defects
differed. The causes did not, and every repair so far treated a symptom:

| Recurring cause | Examples from reviews |
|---|---|
| **Mutable state that can drift from the facts.** Manifest `state`, call counters and a checkpoint are rewritten in place, separately from the records they describe. | The checkpoint trailed its records by one; the manifest count trailed the sealed records; "incomplete" was edited to "running". |
| **Derived data persisted inside facts.** Parsed model output and validator reasons were stored in call records. | A surrogate in a claim id and deep nesting in a junk key made records impossible to seal. |
| **Several files per step, no global order.** Score, receipt, finish and checkpoint seal are separate writes with windows between them. | Crashes after the score, after the finish, and before the anchor each left the run in a different stuck state. |
| **Recovery written per window.** Each fix covered only the crash point that the last review had probed. | R5 fixed one finalization window; R6 found three more. |
| **Writes that are not atomic.** | A kill or full disk left empty or truncated files that no command could get past. |
| **Correctness coupled to telemetry.** | A reopen of the activity log that refused a terminal state blocked `--resume`. |
| **External side effects not retried.** | A failed git commit was never retried. |

R7 removes these causes instead of patching their symptoms.

## 2. Invariants

Every command must preserve all of the following. The tests in §10 check each one mechanically.

- **J1 — one source of truth.** Each run has one append-only **journal**. Everything else about the run is
  either the journal or a **projection** of it.
- **J2 — sealed and chained.** Each journal entry is sealed (a digest over its canonical content). Each entry
  names the seal of the entry before it, and the first entry names the run.
- **J3 — atomic entries.** An entry is written to a temporary file, flushed, fsynced, and then renamed into
  place, and only by the holder of the run lease. A journal on disk is therefore always a *prefix* of the
  journal the program meant to write.
- **J4 — state is replay.** A run's state is a pure function `replay(journal)`. No state field exists anywhere
  that could disagree with the journal.
- **J5 — facts only.** An entry holds what happened: provider evidence, raw model output, coding execution
  evidence, attribution, and decisions. It never holds anything recomputable from other entries, such as
  normalization, validation, parsed output or reasons.
- **J6 — always sealable.** Every value passes through `safe_value` before sealing. That step replaces lone
  surrogates, truncates depth beyond 48, turns non-finite numbers into strings, and drops non-JSON types.
  No model output can make an entry unsealable.
- **J7 — idempotent projections.** A projection (such as `score.json` or a run anchor) is rebuilt from replay.
  Rebuilding an existing projection either leaves it byte-identical or is refused as a conflict. It is never
  silently overwritten.
- **J8 — one command shape.** Every command is `lease → replay → decide → append → project → anchor`. It
  appends at most one entry per decision, so a kill between any two writes leaves a valid prefix, and
  running the same command again converges.
- **J9 — no hand edits.** From every reachable on-disk state, some supported command leads either to
  completion or to a recorded closure that allows the next attempt.
- **J10 — telemetry is inert.** No decision, write or recovery step reads or depends on the activity log.
  Telemetry failures are swallowed.
- **J11 — side effects are retried.** Git anchoring is idempotent, and every command sweeps it again. The
  journal never depends on a git operation having succeeded.
- **J12 — a call is never repeated.** Before every provider call, a `call_started` entry is appended. No
  second `call_started` for the same schedule position can ever be appended. If a call's outcome is not
  durably recorded, the attempt is closed rather than the call re-issued. This keeps the fixed-seed schedule
  executed at most once per attempt, provably.

## 3. Journal format

```
data/g_route3/phase_{a,b}/<run_id>/
    journal/000001.json         run_created
    journal/000002.json         call_started  (schedule position 1)
    journal/000003.json         call_recorded (schedule position 1)
    ...
    journal/000576.json         call_started  (position 288)
    journal/000577.json         call_recorded (position 288)
    journal/000578.json         scored
    journal/000579.json         completed
    quarantine/                 torn tail entries moved aside (never deleted)
    score.json, receipt.json    projections of scored / completed
```

Each entry has the same envelope:

```json
{"entry": 17, "kind": "call_recorded", "previous_entry_sha256": "…", "run_id": "…",
 "at": "UTC timestamp", "payload": { … }, "record_sha256": "seal over everything above"}
```

**Entry kinds and payloads:**

| Kind | Payload | When |
|---|---|---|
| `run_created` | Phase, schedule digest, guarded-dependency digest, freeze digest, synthetic flag, authorization attempt and digest, fixed endpoint, model receipts, and for B the table digest and Phase A run id | First entry, exactly once |
| `call_started` | Schedule position, call id, request-body digest | Immediately before the provider is called, and only if the previous entry closed the previous position |
| `call_recorded` | Schedule position and call id; request-body digest; the provider's raw body (base64) and its sha256; raw output; returned model; provider metrics (scalars only); coding execution evidence and candidate error; `infrastructure_failure` | Immediately after its own `call_started` |
| `note` | `lease_broken` (the holder that died), `tail_quarantined` (file name, reason), `anchor_failed` (for audit only; nothing depends on it) | Any time before a terminal entry |
| `closed` | State (`incomplete`, `failed` or `cancelled`), reason, calls so far | Terminal. At most once, and never after `completed` |
| `scored` | The full score report, as sealed content | Only when every call is recorded |
| `completed` | Receipt: chain head, score seal, manifest seal, freeze and guarded digests | Terminal. Only right after `scored` |

The score is a **journal entry**, not something recomputed at replay time. The Phase B report includes
the outcomes of other attempts at scoring time, so recomputing it later could give a different answer.
Sealing it once makes replay deterministic. Phase A's cells can still be checked by recomputing them from
the `call_recorded` entries, and Phase B preconditions do exactly that. So the `scored` entry is verified
against the facts, not trusted.

## 4. Replay

`replay(entries) → RunState` is pure and total. It returns either a state or an **integrity failure** that
names the first offending entry.

It checks, in order:
- entry numbers are contiguous and every seal verifies;
- the previous-seal chain holds;
- `run_created` is first and unique;
- calls come as pairs: `call_started` k then `call_recorded` k. Positions run contiguously from 1 and
  match the frozen schedule's call ids, and nothing else may appear between the two entries of a pair;
- no entry follows a terminal entry;
- `scored` appears only once every call is recorded;
- `completed` comes immediately after `scored`, and its receipt fields match the replayed chain head and
  score seal.

**Resulting states:**

| State | Meaning | Derived from |
|---|---|---|
| `absent` | No journal | — |
| `created` | Created, no calls | `run_created` only |
| `collecting(k)` | k of N calls recorded | k `call_recorded` entries, 0 < k < N |
| `in_doubt(k)` | Call k was started, but its outcome was not durably recorded | The last entry is `call_started` k, with no `call_recorded` k |
| `faulted(k)` | A recorded call carries `infrastructure_failure`, not yet closed | Any `call_recorded` with a failure, no terminal entry |
| `collected` | Every call recorded, not scored | N `call_recorded` entries, no `scored` |
| `scored` | Scored, not completed | `scored`, no `completed` |
| `completed` | Done | `completed` |
| `closed(s)` | Ended without completing | `closed` |

**Torn tail rule (operator decision 2).** Only the last file can be torn: J3 guarantees it, and only one
writer holds the lease. A torn write therefore means an external fault, such as a full disk or a failing
device. If the last file fails to parse or seal, replay under the lease moves it to `quarantine/` and
appends `note: tail_quarantined`. What happens next depends on which kind of entry was torn:

- **A torn entry about provider execution** (`run_created`, `call_started`, `call_recorded`, or a `note`)
  **closes the attempt.** The command appends `closed(incomplete, durability_uncertain: <entry>)`. If the
  journal is empty after quarantine, a minimal `run_created (recovered)` is written first. We cannot prove
  whether the call happened or was recorded, so the call is never repeated. The next governed attempt is
  required.
- **A torn `scored` or `completed` entry** is quarantined, and the entry is re-derived from facts already
  on record. This is a refinement of decision 2, flagged for review: those entries are recomputed from the
  sealed calls, so no call is repeated and no provider outcome is in doubt.

A bad file anywhere else in the journal is an integrity failure. It can only come from outside the program,
so it is reported and never repaired.

**A temporary file left by a kill before its rename** is not part of the journal and is ignored. If it held
a `call_recorded`, the journal ends in `call_started`, which is `in_doubt`, and the attempt is closed. The
temporary file is moved to `quarantine/` on the record, for audit.

## 5. Commands as a state machine

Every command takes the lease, replays, then acts. "Append" means one atomic journal write.

| State | `launch` (fresh attempt) | `--resume` | `--abandon` | `--clear-orphan` |
|---|---|---|---|---|
| `absent`, attempt consumed | n/a | append `run_created`, then collect | append `run_created` + `closed(incomplete)` | refused (the ledger owns it) |
| `absent`, no attempt | consume the attempt, append `run_created`, collect | refused | refused | n/a |
| `created` / `collecting(k)` | refused (latest attempt still open) | collect from k+1 | append `closed(incomplete, abandoned: reason)` | refused (the ledger owns it) |
| `in_doubt(k)` | refused | append `closed(incomplete, call_outcome_unknown: k)` | same as resume | refused |
| `faulted(k)` | refused | append `closed(incomplete, infrastructure_failure)` | same as resume | refused |
| `collected` | refused | score: append `scored`, then `completed` | refused (finish it instead) | refused |
| `scored` | refused | append `completed` | refused | refused |
| `completed` | refused (no best-of-N) | re-project and re-anchor only | refused | refused |
| `closed(s)` | the next attempt is allowed | refused | refused | refused |
| journal in the fixed root, not in the ledger | refused (root disagrees with the ledger) | refused | refused | allowed only with no `call_recorded`; the record is written and anchored, then the folder is moved |

**Scoring failure.** If computing the report raises, the command appends `closed(failed, scorer_integrity_failure)`.

**Dependency drift.** A guarded dependency that changes mid-run, or before a resume, appends
`closed(incomplete, guarded_dependency_drift)`.

**Resume after a provider exception.** A provider exception after `call_started` k appends
`closed(incomplete, provider_boundary_exception)` in place of `call_recorded` k. That is the zero-retry policy:
no provider call is ever issued twice for one position in one attempt (J12).

## 6. Crash-window analysis

Because of J3 and J8, the only thing a kill can leave behind is a **prefix of the intended journal**, plus
possibly a finished or unfinished projection or git commit. Here is every write, with the state a kill just
after it leaves and the command that recovers:

| Write (in order) | State after a kill here | Recovered by |
|---|---|---|
| Lease file | stale lease | Any command. It breaks a lease whose process is dead on this host, and records `note: lease_broken`. |
| Ledger entry (attempt consumed) | `absent`, attempt consumed | `--resume` creates the run, or `--abandon` closes it |
| `run_created` | `created` | `--resume` / `--abandon` |
| `call_started` k | `in_doubt(k)` | `--resume` closes the attempt as `call_outcome_unknown`. The next attempt is required, and the call is never repeated. |
| Temporary file of `call_recorded` k, not renamed | `in_doubt(k)` (temporary file quarantined) | Same as above |
| `call_recorded` k | `collecting(k)` or `faulted(k)` | `--resume` (continues, or closes if faulted) |
| Torn `run_created` / `call_started` / `call_recorded` (disk full, external) | Tail quarantined on the next command | The attempt is closed as `durability_uncertain`. The next attempt is required, and nothing is repeated. |
| Torn `scored` / `completed` (external) | Tail quarantined | `--resume` re-derives it (no call involved) |
| `closed` | `closed` | Next attempt |
| `scored` | `scored` | `--resume` appends `completed` |
| `completed` | `completed` | `--resume` re-projects and re-anchors |
| Projection file (score / receipt / anchor) | Stale or missing projection | Every command re-projects (J7) |
| Git commit | File written but not committed | Every command sweeps the anchors again (J11). Phase B refuses until the files are committed. |

There are **no other writes**. The launcher is the only entry point, and it performs only these. The test
harness in §10 enumerates the writes automatically, so this table cannot silently fall out of date.

## 7. Durability and the lease

**Atomic write.** Write to a temporary file in the same directory, flush, `fsync`, then `os.replace`. Where
the OS supports it, the directory is fsynced after the rename. Exclusive creation is checked under the
lease. A leftover temporary file never matches a journal name, so it is ignored.

**Lease.** One lease per phase run root. It records the process id, host and creation time. A stale lease
(same host, dead process) is broken and recorded. Liveness is checked with `OpenProcess` and
`GetExitCodeProcess` on Windows, and with `kill(pid, 0)` on POSIX. It must **never** use `os.kill` on
Windows, because that terminates the process. A lease held from another host is never broken.

## 8. The attempt ledger (cross-run journal)

The per-phase authorization ledger keeps its role. It is the journal of *attempts*: hash-chained, written
atomically, and anchored in git as each entry is consumed.

An attempt's outcome is `replay(run journal).state`. A committed run anchor also counts as proof of
completion, so deleting a receipt cannot reopen a finished attempt. The attempt policy is unchanged:

- attempt n+1 is allowed only when every earlier attempt is `closed`;
- the first `completed` attempt is the result;
- every attempt, with its outcome, reason and number of recorded calls, is disclosed in the table and in
  the Phase B score.

## 9. Projections, anchors and Phase B

**Projections.** These are all rebuilt by replay:

- `score.json` (from `scored`);
- `receipt.json` (from `completed`);
- `run_anchors/phase-X-<run>.json` (chain head, score seal, receipt seal, attempt);
- `run_anchors/phase-X-<run>-closed.json` (from `closed`);
- the orphan record.

**Anchoring.** Each command starts and ends with an anchor sweep, an idempotent commit of every ledger
entry, run anchor and the frozen table.

**Phase B** requires three things:

1. The Phase A journal replays to `completed`.
2. The recorded cells, recomputed from the `call_recorded` entries, equal the `scored` cells and the table.
3. The ledger, the run anchor and the table are committed and unmodified in git.

The provider-evidence checks read the raw bodies in the `call_recorded` entries.

## 10. Verification strategy (class-level, not instance-level)

**Where each part runs (operator decision 3).**
- The **exhaustive** crash campaign below is part of **freeze certification**. Its complete results are
  recorded in a certification report that the execution freeze binds by digest.
- The normal test suite runs a **representative deterministic recovery subset** that is quick. It covers
  one kill point of each kind: before and after each entry kind, a leftover temporary file, a torn tail of
  each kind, a stale lease, a failed git anchor, and each launcher command.

The reviewers asked for evidence that the *class* is closed. The core test is a **crash-injection harness**:

1. Run a complete synthetic Phase A (and B) once, uninterrupted. Record the sequence of write operations,
   and the final journal content without timestamps.
2. For **every** write index *w* in that sequence, re-run from scratch and kill the process just after
   write *w*. Where relevant, also kill just before the rename, to leave a temporary file, or leave a
   truncated file, to simulate a torn write.
3. From each killed state, apply only supported launcher commands (`--resume`, or `--abandon` followed by
   a next attempt). Assert that each ends in one of two states:
   - (a) `completed`, with a journal and score equal to the uninterrupted run apart from recorded notes;
   - (b) `closed`, with a recorded reason and a next attempt that completes.

   Assert also that, **across every attempt in every case, no schedule position was sent to the provider
   twice within one attempt (J12).** The stub provider counts calls per attempt and position.
4. Assert that no case needs a hand edit, and that the attempt disclosure is correct in every case.

Additional class tests:
- a **replay property test**: random entry sequences are either rejected with a precise reason or give
  one of the §4 states;
- a **sealability fuzz**: arbitrary Python and JSON values, including surrogates, deep nesting and
  non-finite numbers, are always sealable after `safe_value`;
- a **launcher-level run**: the real launcher, with `GovernedOllamaProvider` replaced by a stub and git
  pointed at a throwaway repository, run through launch, kill, resume, freeze-table, Phase B and resume.

## 11. What changes from R6

| Area | R6 | R7 |
|---|---|---|
| Run store | G-ROUTE1 `RouteRunStore`: mutable manifest, checkpoint, several terminal files | G-ROUTE3 journal store, append-only and replayed (G-ROUTE1 is untouched) |
| Call record | Facts plus stored evaluations | Facts only; evaluations recomputed |
| State | Fields in `run.json` and `checkpoint.json` | `replay(journal)` |
| Finalization | `_finalize` with idempotent steps across files | Two journal entries (`scored`, `completed`) plus projections |
| Recovery | Per-window code | One command shape (J8), checked by exhaustive crash injection |
| Telemetry | In the terminal-view agreement | Inert (J10) |
| Scientific design | — | Unchanged |

The grading fixes from the R6 fixture review are independent of the lifecycle and would ship alongside:

- dash and space normalization;
- rejecting a duplicate Answer line;
- the synthesis verbatim check;
- disclosure of the recursion rule and the missing operators;
- the quadratic regex bound.

**Files.** New: `tools/g_route3_journal.py`, which replaces the `g_route3_store.py` draft. Rewritten:
`tools/g_route3_runner.py` and the lifecycle parts of `tools/g_route3_launch.py`. The qualification,
validation and routing modules gain one helper each to evaluate fact-only records. The tests gain the crash
harness.

The freeze moves to R7. It supersedes R1 to R6, and all of them stay preserved.

## 12. Operator decisions (2026-09-24)

1. **One append-only journal per run is the authoritative history.** Truth is not split across files by
   type. Derived artifacts may exist for convenience, but only as projections of the journal, never as
   co-equal state.
2. **After a torn write or full-disk event, close the attempt rather than silently repeat the call.** If we
   cannot prove whether the provider call happened and was durably recorded, repeating it would make it
   ambiguous whether the fixed-seed schedule ran once or twice. The uncertainty is recorded, the attempt is
   closed, and the next governed attempt is required.
   - Implemented by the torn-tail rule (§4) and the write-ahead `call_started` entry (J12). The entry extends
     the same principle to a kill between the provider's reply and the durable record.
   - One refinement is flagged for review: torn `scored` and `completed` entries are re-derived, not closed.
3. **The exhaustive crash harness runs at freeze certification**, not on every normal test run. Normal
   development uses a quick, representative, deterministic recovery suite.
4. **Two-stage review.**
   - Design review now, by two fresh read-only reviewers. Reviewer A covers journal and replay correctness
     and recoverability. Reviewer B covers scientific integrity and authorization and attempt semantics.
   - Implementation review later, by fresh reviewers who check that the code implements this contract and
     that the crash harness proves it.
5. **The partial drafts are neither deleted nor used.** `tools/g_route3_store.py` and
   `tools/g_route3_runner_new.py` stay untracked and unwired until this design is accepted. After
   acceptance, each is either rewritten against the approved design or deleted. Existing code does not
   decide the architecture.

Provider generation calls for this design: **0**. Scientific runs launched: **0**.
