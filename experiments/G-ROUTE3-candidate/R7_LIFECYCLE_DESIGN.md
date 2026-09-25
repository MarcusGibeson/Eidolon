# G-ROUTE3 R7 — journal/replay lifecycle architecture (design revision 2)

Status: **design-review candidate, revision 2.** Revision 1 (commit `80a10d9`, document digest `e4c9c8f6…`)
went to two independent design reviewers. Reviewer A found 12 blocking defects and Reviewer B found 6
(`R7_DESIGN_REVIEW_ROUND1.md`). This revision answers every finding, and it incorporates the operator's
rulings of 2026-09-24 and 2026-09-25 (§21).

It changes **nothing scientific**: corpora, gold, validators, prompts, the qualification rule, routing,
gates, thresholds and denominators are all untouched. Five grading changes found by the R6 fixture reviewer
are handled separately; see §22. No implementation is wired in, no execution freeze is written, no provider
is contacted, and no scientific run is launched.

**Review sequence.**
1. Design review of this revision, by fresh reviewers.
2. If clean, implement from this document.
3. Implementation review, with fresh reviewers and the certification crash campaign.
4. Only then is an R7 execution freeze offered for authorization.

---

## 1. What this lifecycle must guarantee

A G-ROUTE3 phase attempt sends a fixed-seed schedule of provider calls: 288 for Phase A, 144 for Phase B.
That record is used as scientific evidence, so the lifecycle must guarantee:

- **G1 — at most once.** No schedule position is sent to the provider twice within one attempt, whatever
  crashes, power losses, disk faults or cheap tampering occur.
- **G2 — truthful history.** The recorded history never misstates what happened. Anything that cannot be
  proven (for example, whether an interrupted call reached the provider) is recorded as uncertain and
  disclosed. It is never guessed.
- **G3 — no best-of-N.** An attempt whose results are visible cannot be discarded in favour of another
  attempt. Where the design cannot mechanically prevent optional stopping, it discloses it.
- **G4 — always a way forward.** Every reachable on-disk state has a supported command that leads either to
  completion or to a recorded, disclosed closure. The one exception is a recorded integrity failure, which
  requires a distinct operator authorization (§21, ruling 9).
- **G5 — determinism.** The same journal always replays to the same state. Every derived entry can be
  recomputed byte for byte from the entries before it.

**Threat model** (operator ruling). This is an honest operator with tamper-evident records.

- **In scope:**
  - accidents, including crashes, kills, **power loss**, a full disk, sharing violations and antivirus
    interference;
  - misuse through any supported command;
  - cheap tampering, such as deleting, truncating or editing a few files.
- **Out of scope:** a deliberate local adversary who runs a fake model server, uses a second checkout, or
  consistently rewrites sealed files together with the git evidence ref. The git evidence ref (§13) makes
  cheap tampering visible.

## 2. Invariants

- **J1 — one authority per run.** Each run has one append-only **journal**. The attempt **ledger** (§9) is a
  second append-only journal, one per phase, that records the attempts. Every other file is either a
  projection of these or a non-authoritative log.
- **J2 — sealed and chained.** Every journal and ledger entry is sealed with its canonical digest (§4.4) and
  names the seal of the entry before it.
- **J3 — durable, non-overwriting publication.** An entry becomes part of the journal only through the
  publication protocol in §14. That protocol writes a temporary file, flushes it, renames it with write-through
  and without overwrite, and then flushes the directory. So a published entry survives power loss, and
  publication never overwrites an existing entry.
- **J4 — pure replay.** `replay(files) → (state, observations)` is a pure, total function of the directory
  listing and file bytes. It never writes anything. Repairs are made only by `recover()` (§6), and only by
  the lease holder.
- **J5 — facts only.** Journal entries hold facts: provider evidence, raw model output, sandbox evidence,
  attribution and decisions. They never hold anything that can be recomputed from other entries.
- **J6 — always sealable.** Every value passes through `safe_value` before it is sealed. That function
  replaces lone surrogates, truncates nesting deeper than 48, turns non-finite numbers into strings, and
  turns non-JSON types into strings. Raw model text is stored as **base64** plus its UTF-8 text sha256, so
  antivirus never sees executable-looking plaintext.
- **J7 — deterministic derived entries.** The `scored` and `completed` payloads, and every projection, are
  pure functions of earlier entries. They contain no clock, host name or process id. If a derived entry is
  re-derived and does not match what already exists, that is an integrity failure. It is never overwritten.
- **J8 — one command shape.** Every command runs `lease → evidence sweep → replay → recover → decide →
  (one write) → re-replay → …`. Each step is a single publication, so a kill between any two writes leaves a
  state that `replay` classifies and some command continues from (§8).
- **J9 — way forward.** Guarantee G4 holds for every reachable state. The crash campaign in §19 checks it.
- **J10 — telemetry is inert.** Activity, telemetry and the recovery log are never read by `replay`,
  `recover` or any decision.
- **J11 — evidence before contact.** Before the first provider call of an attempt, the ledger entry must be
  committed to the git evidence ref. Before every call, an intent record for that call must be committed
  too (§13).
- **J12 — at most once.** A call is sent only after its `call_started` entry is published durably and its
  intent is committed. No second `call_started` for the same position can be published. If the outcome of a
  started call is not durably recorded, the attempt is closed and the call is never repeated.
- **J13 — no closure after `scored`.** Once `scored` exists, the only permitted next entry is `completed`.
  Dependency drift in `collected` or `scored` makes commands **refuse** (restore the dependencies). It never
  closes the attempt.
- **J14 — zero transport retries.** The provider adapter performs exactly one HTTP request per call, with no
  adapter-level retries. This is part of the provider contract and has its own test (§19).

## 3. Files

```
data/g_route3/phase_{a,b}/<run_id>/
    journal/000001.json ...     published journal entries (authoritative)
    journal/000123.torn         a torn entry renamed in place by recover() (still visible to replay)
    journal/.tmp-*              temporary files (never journal entries; replay reports them)
    recovery.log                non-authoritative side log: lease breaks, sharing-retry counts, anchor failures
    score.json, receipt.json    projections of `scored` and `completed`
experiments/G-ROUTE3-candidate/authorization_ledger/phase-{A,B}-000001.json ...   the attempt ledger journal
experiments/G-ROUTE3-candidate/run_anchors/...                                      projections for review in git
refs/g-route3/evidence      a dedicated git ref: evidence commits made with plumbing (§13)
```

Replay considers only files named `NNNNNN.json` or `NNNNNN.torn` in `journal/`. It reports and ignores
anything else, such as `desktop.ini`. The quarantine directory is gone: torn files stay in place, renamed,
so that replay sees them.

## 4. Journal entries

### 4.1 Envelope

```json
{"entry": 17, "kind": "call_recorded", "previous_entry_sha256": "<seal of entry 16, or the ledger entry's seal for entry 1>",
 "run_id": "…", "payload": { … }, "record_sha256": "<seal of everything above>"}
```

There is no timestamp inside the seal. Times are recorded by the evidence commits and the recovery log.

### 4.2 Kinds and payloads

| Kind | Payload | Allowed after (ignoring nothing; there are no notes in the journal) |
|---|---|---|
| `run_created` | Phase, attempt number, authorization digest, the claimed ledger position; schedule, guarded-dependency and freeze digests; synthetic flag; fixed endpoint; model receipts; transport contract; for Phase B, the table digest and Phase A run id | First entry only |
| `call_started` | Position k, call id, request-body digest, guarded digest observed now, the seal of the intent commit (§13) | `run_created` (k = 1); `call_recorded` k−1 of a non-coding call; `execution_recorded` k−1 of a coding call |
| `call_recorded` | Position k; provider raw body (base64) and its sha256; raw output (base64) and its text sha256; returned model; scalar metrics; `transport_failure` (empty unless the provider boundary raised) | `call_started` k |
| `execution_recorded` | Coding calls only: position k, sandbox evidence, candidate error, `infrastructure_failure` | `call_recorded` k, when k is a coding call |
| `scoring_started` | Digest of the fact prefix it will score | Every position recorded (and executed, for coding calls), with no terminal entry |
| `scored` | The score report: a pure function of the fact prefix (§4.3) | `scoring_started` |
| `completed` | The receipt: chain head seal, `scored` seal, `run_created` seal, freeze and guarded digests | `scored` only |
| `closed` | State (`incomplete`, `failed` or `cancelled`), a reason from a closed list, `calls_started`, `calls_recorded`, the in-doubt position if any, exception class and message if any, the numbers and sha256 of any `.torn` files it acknowledges | Any entry that is not terminal, **except** `scored`, which may be followed only by `completed` (J13) |

`transport_failure` in `call_recorded`, and `infrastructure_failure` in `execution_recorded`, make the next
decision `closed(incomplete, …)`. The call is never retried.

### 4.3 Determinism of derived entries

The `scored` report is computed only from:

- the fact entries of this run;
- the frozen corpora, gold and table (bound by the digests in `run_created`);
- for Phase B's attempt disclosure, the ledger entries and the terminal states of *earlier* attempts, which
  are immutable once terminal.

This run itself is described as `collected` in that disclosure. The report contains no clock. `completed`
is the fixed receipt described above. Re-deriving either always yields the same bytes.

### 4.4 Canonical JSON

A seal is the sha256 of the UTF-8 encoding of:

    json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

where `value` has already passed through `safe_value`. Integers of 10^30 or more become strings. Floats use
Python's shortest round-trip `repr`.

## 5. Replay: an ordered decision procedure

`replay(files)` is pure. It lists `journal/`, parses each `NNNNNN.json`, and records each `.torn` and
temporary file as an **observation**. Then it applies these rules **in order; the first match wins**:

| # | Condition | State |
|---|---|---|
| R0 | No journal directory | `absent` |
| R1 | Any `NNNNNN.json` other than the last fails to parse or seal, a chain link is broken, numbering has a gap, or the grammar of §4.2 is violated before the last entry | `integrity_failure(<first offending entry>)` |
| R2 | The last `.json` fails to parse or seal | `torn_tail(n, predicted_kind)`. The kind is predicted from the grammar and the previous entry; if it cannot be predicted uniquely, it is treated as a provider-execution kind. |
| R3 | A `.torn` file exists that no later `closed`, re-derived `scored` or re-derived `completed` acknowledges | `torn_pending(n, predicted_kind)` |
| R4 | The last entry is `completed` | `completed` |
| R5 | The last entry is `closed` | `closed(state, reason)` |
| R6 | The last entry is `scored` | `scored` (needs `completed`) |
| R7 | The last entry is `scoring_started` | `scoring_interrupted` |
| R8 | The last entry is `call_started` k | `in_doubt(k)` |
| R9 | The last entry is a `call_recorded` k with `transport_failure`, or an `execution_recorded` k with `infrastructure_failure` | `faulted(k)` |
| R10 | The last entry is `call_recorded` k for a coding call (with no execution record yet) | `awaiting_execution(k)` |
| R11 | Every position is recorded (and executed, for coding calls) | `collected` |
| R12 | The last entry is `call_recorded`/`execution_recorded` k, where k is less than N | `collecting(k)` |
| R13 | The last entry is `run_created` | `created` |

After that, two cross-checks against the git evidence ref (§13) can override the state:

- If the evidence ref holds an **intent** for position j, but the journal has no `call_started` j, the state
  becomes `in_doubt(j)`. Truncation after a committed intent looks exactly like a crash in the intent window,
  so both are treated conservatively.
- If the evidence ref holds a **journal head** longer than the journal on disk, the state becomes
  `integrity_failure(truncated_below_evidence)`.

## 6. `recover()` (lease holder only; each step is one publication)

| State | Recovery step (one write), then re-replay |
|---|---|
| `torn_tail(n, provider kind)` | Rename `n.json` to `n.torn` in place, with no overwrite. The state becomes `torn_pending`. |
| `torn_pending(n, provider kind)` | Publish `closed(incomplete, durability_uncertain, torn=[n, sha256])` at n+1 |
| `torn_tail(n, scored/completed)` | Rename to `n.torn`, then re-derive (next row) |
| `torn_pending(n, scored/completed)` | Publish the re-derived entry at n+1, naming the torn file. If an existing `score.json`, `receipt.json` or evidence-ref anchor disagrees byte for byte, the state is `integrity_failure(rederivation_mismatch)`. |
| `torn_pending(n, closed)` | Publish `closed` at n+1 with the torn entry's reason if it can be read, otherwise `durability_uncertain` |
| `in_doubt(k)` | Publish `closed(incomplete, call_outcome_unknown, in_doubt=k)` |
| `faulted(k)` | Publish `closed(incomplete, transport_failure` or `infrastructure_failure, …)` |
| `scoring_interrupted` | Re-run the scorer in a subprocess with a timeout. If it succeeds, publish `scored`; if it fails, crashes or times out, publish `closed(failed, scorer_did_not_finish)` (the one closure allowed from `collected`, B#2) |
| `awaiting_execution(k)` | Re-run only the local sandbox for k (no provider involved), then publish `execution_recorded` k |

Temporary files are reported. `recover()` deletes a temporary file only when it names an entry number that
is already published. Any other temporary file is renamed to `.orphan-tmp-<n>` and stays in place.

## 7. Commands

Every command takes the lease, runs the evidence sweep (§13), replays, runs recovery to a fixpoint, and then
applies its action by the recovered state:

| State | launch n | `--resume` | `--abandon` | `--declare-integrity-failure` |
|---|---|---|---|---|
| no journal, attempt n not in the ledger | publish `run_created`, consume the ledger entry (§9), commit it (J11), collect | refused | refused | refused |
| `absent`, attempt consumed (journal deleted) | refused | refused | refused | record at ledger level (§9) |
| `created`, `collecting(k)` | refused | collect from the next position | allowed **only if** its own preflight fails (§9.3) | refused |
| `collected` | refused | publish `scoring_started`, then `scored`, then `completed` | refused | refused |
| `scored` | refused | publish `completed` | refused | refused |
| `completed` | refused (no best-of-N) | re-project and re-sweep only | refused | refused |
| `closed` | the next attempt is allowed | refused | refused | refused |
| `integrity_failure` | refused | refused | refused | allowed: record at ledger level |
| journal in the fixed root, not in the ledger | refused | refused | refused | refused; `--clear-orphan` applies instead (§9.4) |

**Precedence.** Recovery always runs before the command's action. Dependency drift found in `created` or
`collecting` publishes `closed(incomplete, guarded_dependency_drift)`. Drift found in `collected`, `scored`
or `completed` makes the command refuse (J13).

**Run id.** Every command reads the run id from the ledger entry of the attempt it names; it is never a free
argument. `--resume` takes the same verbatim sentence as the launch.

**`--freeze-table`.** Requires the Phase A attempt named in its sentence to replay as `completed`. It builds
the table from the replayed `scored` entry, never from a projection. The attempt disclosure comes from ledger
and replay (§12), and the audit record names the `run_created` and `scored` seals. The table is written with
the §14 protocol and without overwrite, then committed to the evidence ref. A rerun that finds an identical
table is a no-op. A different table is refused. A torn table is renamed to `.torn` and rebuilt, and the
rebuilt table must be identical to the committed one.

## 8. The order of operations for one call (Phase A and B)

1. Guard check (no drift), lease re-verified (§15).
2. Commit **intent(k)** to the evidence ref: the run id, k, the request-body digest, and the current journal
   head. If the commit fails, nothing else happens and the command stops. The state is unchanged, so a
   resume retries the commit.
3. Publish `call_started` k (§14, durable). A crash between steps 2 and 3 gives `in_doubt(k)` through the
   evidence cross-check, and the attempt is closed.
4. Send exactly one provider request (J14).
5. Publish `call_recorded` k, including a `transport_failure` if the provider raised. A crash between steps
   3 and 5 gives `in_doubt(k)`, and the attempt is closed.
6. For a coding call, run the sandbox locally and publish `execution_recorded` k. A crash between steps 5
   and 6 gives `awaiting_execution(k)`, and only the sandbox is re-run.
7. If a failure field is set, publish `closed`.

## 9. Attempts: the ledger journal

### 9.1 Entries

The ledger is a hash-chained journal per phase, published with the §14 protocol. It has two entry kinds:

- `attempt_consumed` records the attempt number, the verbatim sentence, the authorization digest, the run
  id, the fixed run root, and the seal of the attempt's `run_created`.
- `attempt_closed_at_ledger` records the attempt number and a reason, either `integrity_failure` or
  `journal_missing`. It also records the evidence that was observed, and leaves the run folder untouched.

A ledger entry that is torn or missing is judged against the evidence ref, which wins over a shorter ledger
file. The same torn-tail and temporary-file rules apply as for run journals.

### 9.2 Order

On launch, the steps are:

1. Take the lease.
2. Publish `run_created`.
3. Publish `attempt_consumed`, naming the `run_created` seal.
4. Commit that ledger entry to the evidence ref.
5. Collect.

If the process stops between steps 2 and 3, the result is a run folder with no calls that the ledger does
not know about. `--clear-orphan` handles it (§9.4). No call can have happened, because J11 requires the
ledger entry to be committed before any call.

### 9.3 The attempt policy

- **Launching attempt n+1** is authorized only when every earlier attempt of the phase is `closed` or closed
  at ledger level. The first `completed` attempt is the result.
- **`--abandon`** (operator ruling 7) is allowed only when the command's own preflight fails. That preflight
  checks the model receipts against the frozen bindings, the provider version, the guarded dependencies and
  the freeze's validity. The closure reason is the list of failing checks, recorded automatically. There is
  no free-text abandon.
- **A kill during a call** leads to `in_doubt`, and that attempt closes. Optional stopping by killing a
  process cannot be prevented mechanically, so it is **disclosed** instead (§12).

### 9.4 Orphans and integrity failures

- **`--clear-orphan`** accepts only a run folder that has no `call_started` entry and no ledger entry. It
  commits an orphan record to the evidence ref first, then moves the folder with an atomic, non-overwriting
  rename inside the same directory tree. Orphans are disclosed.
- **`--declare-integrity-failure`** (operator ruling 9) publishes `attempt_closed_at_ledger(integrity_failure)`
  and commits it. The folder is left as found. The next attempt then requires the distinct sentence
  `Authorize G-ROUTE3 phase <P> execution <binding> attempt <n> after integrity failure of attempt <n-1>`.

## 10. Phase B preconditions (stated against journals)

Phase B may contact the provider only if all of these hold:

1. The Phase A attempt named in the table replays as `completed`, at the fixed root, with no `.torn` file
   left unacknowledged.
2. It is the **only** completed Phase A attempt. Every other Phase A attempt is closed or closed at ledger
   level.
3. The authorization attempt and digest in its `run_created` equal its ledger entry. That ledger entry names
   the `run_created` seal.
4. It is not synthetic. It ran under this freeze. Its guarded digest (in `run_created`, and observed in every
   `call_started`) equals today's. Its recorded model receipts verify, and its endpoint is the fixed endpoint.
5. For every call, the provider evidence is consistent: the raw body's sha256 matches, the envelope's model
   equals the request, and the decoded output equals the recorded output. The request digest equals the
   schedule's.
6. Cells re-derived from its fact entries equal the `scored` cells and the table's cells.
7. The table's source names the `scored` seal and the `run_created` seal. The table's attempt disclosure
   equals the disclosure computed now (§12). The audit names both seals and is not a frozen artifact.
8. The evidence ref contains every Phase A ledger entry, the run anchor, every closed anchor, every orphan
   record and the table. Every journal head on disk is at least its evidence high-water mark.
9. Phase B's own authorization names the freeze, the table, the Phase A run and attempt n, and is consumed
   through §9.

## 11. Durability, in one paragraph

- **Publication.** An entry is published by write-through, non-overwriting rename, followed by a directory
  flush (§14). So a published entry survives power loss, and nothing is ever overwritten.
- **Truncation.** A journal truncated below its git high-water mark is an integrity failure.
- **Lost `call_started`.** A `call_started` that power loss erased is caught by the committed intent, which
  gives `in_doubt`, so the attempt is closed and the call is never repeated.
- **Torn and temporary files.** Torn files stay visible in place until a later entry acknowledges them.
  Temporary files never become entries by accident.

## 12. Disclosure

Both the qualification table and the Phase B score disclose every attempt of the phase:

- attempt number, run id and outcome (`completed`, `closed(state, reason)`, `closed_at_ledger(reason)`);
- `calls_started`, `calls_recorded` and the in-doubt position, if any;
- for every closed attempt, the **partial cells re-derived from its recorded calls**;
- for every seeded position recorded in more than one attempt, whether the raw-output sha256 values are
  **identical** across those attempts. This makes re-sampling and optional stopping visible;
- orphans cleared, and integrity failures declared.

## 13. The git evidence ref (operator ruling 8)

Evidence commits go to `refs/g-route3/evidence`. They are made with plumbing and a **private index**:
`GIT_INDEX_FILE`, `hash-object -w`, `mktree` or `write-tree`, `commit-tree`, then
`update-ref refs/g-route3/evidence <new> <expected-old>`, run with `-c core.fsync=all`. So the evidence ref:

- never touches the working branch, the shared index or `index.lock`;
- never runs hooks;
- fails atomically if another writer moved the ref.

Each commit adds or updates files under a fixed tree: ledger entries, the per-run evidence file (intents and
journal high-water mark), run anchors, closed anchors, orphan records and the table.

**The evidence sweep.** At the start of every command, anything on disk that should be in the evidence ref
but is not gets committed.

**Failure handling.**

- A commit failure *before a provider call* stops the command before the call (J11).
- A commit failure after a call is re-applied by the next sweep. Phase B refuses until the evidence is
  complete.
- Anchor failures are logged in `recovery.log`, never in the journal.

**Git version.** The preflight requires a git version that supports `core.fsync`.

## 14. Publication protocol

To publish `path` with content `bytes`:

1. Write the bytes to `dir/.tmp-<entry>-<token>`, then flush them to disk (`FlushFileBuffers` on Windows,
   `fsync` on POSIX).
2. **Windows:** `MoveFileExW(tmp, path, MOVEFILE_WRITE_THROUGH)` **without** `MOVEFILE_REPLACE_EXISTING`, so
   the call fails if `path` exists. Then open the directory with `FILE_FLAG_BACKUP_SEMANTICS` and
   `FlushFileBuffers` it.
   **POSIX:** `link(tmp, path)`, which fails if `path` exists, then `unlink(tmp)`, then `fsync` the directory.
3. **Sharing violations** (WinError 5 or 32, typically antivirus or indexing) are retried up to 20 times,
   100 ms apart. If they persist, the command aborts without publishing. The state is unchanged, except that
   an aborted `call_recorded` leaves `in_doubt`, which closes that attempt on the next command.
4. **Before every publication**, the lease file is re-read and its token must be this process's (§15).

## 15. The lease

The lease file `<run root>/.lease` holds a random token, the process id, the process creation time (from
`GetProcessTimes` on Windows and `/proc/<pid>/stat` on POSIX) and the host name. It is published with the
§14 no-overwrite protocol.

**When a lease is stale.** It is stale only when the host is this host and either:

- no process with that id exists; or
- a process with that id exists but has a different creation time (the id was reused).

On Windows, liveness is checked with `WaitForSingleObject(handle, 0)`. `ACCESS_DENIED` from `OpenProcess`
means the process is alive. `os.kill` is never used. A lease file that is empty or unreadable is treated as
stale only if it is older than 60 seconds and no process holds it open.

**Breaking a stale lease.** The breaker renames the stale file to `.lease.broken-<token>`. Only one breaker's
rename succeeds. The winner then creates a new lease. Lease breaks are logged in `recovery.log`.

## 16. Out of the journal

Three things are deliberately kept out of the journal:

- **Telemetry and the activity log** (J10).
- **`recovery.log`.** It is append-only, non-authoritative and never read by a decision. It holds lease
  breaks, sharing-retry counts and anchor failures. It replaces revision 1's `note` entries, which broke
  the grammar (Reviewer A, finding 2).
- **Timestamps.** These come from the evidence commits and the recovery log.

## 17. Transport contract (J14)

The provider adapter makes exactly one `POST /api/generate` per call. It uses a `requests.Session` whose
adapters have `max_retries=0`, and it follows no redirects. A test asserts this, using a local stub server
that counts requests.

## 18. Crash and write table

Every write in the system, and its recovery, **includes the writes that recovery itself makes**:

| Write | Recovery from a kill just after it (or during it) |
|---|---|
| Lease temporary file and publish | Stale-lease rule (§15) |
| `run_created` | `created`, or an orphan if the ledger entry is missing (clear-orphan; no call is possible) |
| Ledger `attempt_consumed` | Evidence commit pending; the sweep commits it before any call |
| Evidence intent(k) | `in_doubt(k)` through the cross-check, which closes the attempt |
| `call_started` k | `in_doubt(k)`, which closes the attempt |
| `call_recorded` k | `collecting` or `awaiting_execution` or `faulted`, which continues or closes |
| `execution_recorded` k | `collecting` or `faulted` |
| `scoring_started` | `scoring_interrupted`: re-score in a subprocess, or close as failed |
| `scored` | Publish `completed` |
| `completed` | Projections and sweep |
| `closed` | Next attempt |
| Projection files | Rebuilt; a mismatch with committed evidence is an integrity failure |
| Rename to `.torn` (recovery) | `torn_pending`, which continues to its closure or re-derivation |
| Closure or re-derived entry after `.torn` (recovery) | Terminal, or normal flow |
| Temporary file left by any of the above | Reported. Deleted only if it duplicates a published entry, otherwise renamed `.orphan-tmp` |
| Ledger `attempt_closed_at_ledger` | Committed by the sweep |
| Orphan record commit, then folder move | Re-run `--clear-orphan`. Idempotent: the record exists, then the move completes |
| Table publish and commit | Identical rerun is a no-op; a torn table is rebuilt identically or is an integrity failure |
| Power loss after any of these | Published entries survive (§14). An evidence intent without a `call_started` gives `in_doubt`. A journal shorter than its evidence high-water mark gives `integrity_failure` |

## 19. Verification

**Certification campaign** (operator ruling 3). It runs at freeze certification, and the freeze binds its
report.

- **Choke point.** Every filesystem write and every git plumbing call goes through one I/O layer. Harness
  mode records the sequence of operations.
- **Kill campaign.** For every operation index in an uninterrupted synthetic run (Phase A, table, Phase B):
  kill just after it, and just before its rename. Then apply the supported commands. **Recursively kill
  again at every operation those recovery commands perform**, to depth 2 and then to a fixpoint on novel
  states.
- **Power-loss campaign.** A fault-injecting layer drops every operation not yet flushed to disk (§14),
  and reorders unflushed renames.
- **Oracles.**
  - (a) End state `completed`, whose sequence of *fact payloads* equals the uninterrupted run's, or `closed`
    with a truthful recorded reason, after which the next attempt completes.
  - (b) J12: the stub provider counts sends per attempt and position, and every count must be at most 1.
  - (c) Disclosure: the §12 disclosure matches ground truth.
  - (d) No hand edit ever.
- **Grammar-directed property tests.** Sequences of entries are generated from §4.2 and mutated by
  truncation, gaps, swaps, duplicates and torn tails. Replay must classify every one per §5, and be
  deterministic.
- **Transport test** (§17).

**The normal test suite** (operator ruling 3) runs a quick, representative, deterministic subset covering
one kill point of each kind, each §5 state, each §7 command, lease breaking and evidence failure.

## 20. Contract clauses this design supersedes (Reviewer B, finding 12)

The following R6 wording in `QUALIFICATION_CONTRACT.md` and the freeze is replaced once R7 is implemented,
and it will be re-reviewed with the implementation:

- "consumed ... only once the run exists and holds its lease" is replaced by §9.2 (lease, `run_created`,
  ledger, evidence commit, calls).
- "the unsealed run manifest also reads `complete`" and "five-view terminal agreement" are replaced by
  replay state `completed` (§5).
- The per-record attempt and authorization fields are replaced by `run_created` and the ledger (§10.3).
- "anchors are always re-applied" and "the launcher commits locally" are replaced by the evidence ref with
  plumbing (§13). No branch commits.
- The mutation-guard evidence per record is replaced by the guarded digest observed in every `call_started`.

## 21. Operator decisions and rulings

**2026-09-24**

1. One append-only journal per run is the authoritative history. Derived artifacts are projections only.
2. After a torn write or full-disk event, close the attempt rather than repeat the call (§6).
3. Run the exhaustive crash harness at freeze certification, and a quick representative suite in normal
   development (§19).
4. Two-stage review: the design, then the implementation.
5. The partial drafts `tools/g_route3_store.py` and `tools/g_route3_runner_new.py` stay untracked and
   unwired until the design is accepted. After acceptance they are rewritten against it or deleted. They do
   not decide the architecture.

**2026-09-25, after the round-1 design review**

6. **Torn `scored` or `completed` entries are re-derived byte for byte.** A mismatch is an integrity failure;
   it never closes the attempt and never allows a retry (§6, J7). This explicitly ratifies the refinement of
   ruling 2.
7. **Abandon only when verified stuck,** with disclosure of partial cells and cross-attempt output
   comparison (§9.3, §12).
8. **Evidence is committed before every provider call,** to a dedicated git ref, using plumbing and a private
   index (J11, §13).
9. **An integrity failure is recorded at ledger level.** The next attempt needs the distinct sentence
   acknowledging the failed attempt (§9.4).

## 22. Out of scope: grading changes

The R6 fixture reviewer found five grading issues:

- dash and space normalization;
- a duplicate Answer line;
- a synthesis verbatim check;
- disclosure of the recursion rule and of the missing operators;
- a regex bound.

These change validators, and possibly prompts and corpus digests, so they are a **scientific change**.
They are not part of this lifecycle design. They get their own change record, listing every affected
digest, a re-run of the fixture construction checks, and their own review, separate from this document.
Their findings are recorded in `EXTERNAL_REVIEW_ROUND6.md`.

Provider generation calls for this design: **0**. Scientific runs launched: **0**.
