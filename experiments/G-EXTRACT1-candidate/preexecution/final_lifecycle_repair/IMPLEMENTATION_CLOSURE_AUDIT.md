**Overall: BLOCKED**
One P2 finding. Audit stopped immediately after the paired exception proof. No source repair or second review.

**P2 Finding**
Transport-raised `KeyboardInterrupt` and `SystemExit` allow collection after an external catch.

The transport handler and outer guard catch `Exception`, not these `BaseException` subclasses. After writing START and marking the call attempted, neither exception closes the call nor retains a terminal event. `_operable()` consequently permits the next scheduled call. Sources: [transport boundary](/C:/Users/marcu/Eidolon-g4adj/tools/g_extract1_runner.py:361), [guard](/C:/Users/marcu/Eidolon-g4adj/tools/g_extract1_runner.py:90), [continuation check](/C:/Users/marcu/Eidolon-g4adj/tools/g_extract1_runner.py:217).

Both actual `Run` cases produced:

| Observation | KeyboardInterrupt | SystemExit |
|---|---|---|
| Exception escapes to external catch | Yes | Yes |
| Journal immediately afterward | START | START |
| Retained events / synthetic verdict | `[]` / `null` | `[]` / `null` |
| Next scheduled transport invoked | **Once** | **Once** |
| Journal after continuation | START, START, COMPLETE | START, START, COMPLETE |
| Reconstruction before/after continuation | Rejects unreceipted omission | Rejects unreceipted omission |

Reconstruction emits `SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT`, a frozen INVALID event. It protects restart, but cannot undo the additional transport invocation.

This is **not merely a scoped shutdown limitation**. Propagating a control-flow exception may be appropriate; allowing event-free collection after it is caught violates the frozen omission/interruption semantics. No receipt, checkpoint verification, or authorized abort justified continuation. See [frozen classifications](/C:/Users/marcu/Eidolon-g4adj/experiments/G-EXTRACT1-candidate/DESIGN_CANDIDATE.json:7823).

**Reproduction Evidence**
Independent probe: [audit.py](/C:/Users/marcu/AppData/Local/Temp/G-EXTRACT1-independent-20261004-2a3bda95/audit.py:260). It calls `perform(a[0])` with the raising transport, catches externally, calls `perform(a[1])`, and reconstructs both histories.

- [KeyboardInterrupt evidence](/C:/Users/marcu/AppData/Local/Temp/G-EXTRACT1-independent-20261004-2a3bda95/LR2_control_KeyboardInterrupt/CONTROL_EXCEPTION_EVIDENCE.json)
- [SystemExit evidence](/C:/Users/marcu/AppData/Local/Temp/G-EXTRACT1-independent-20261004-2a3bda95/LR2_control_SystemExit/CONTROL_EXCEPTION_EVIDENCE.json)
- [Blocked report](/C:/Users/marcu/AppData/Local/Temp/G-EXTRACT1-independent-20261004-2a3bda95/BLOCKED.json)

**Audit Matrix**
| Requirement | Result |
|---|---|
| LR1 | PASS: 34 correctly sealed malformed payloads and six malformed envelopes. CORRUPTED_CHECKPOINT retained; INVALID interpretation; original-resume and next-call attempts rejected after catch/reconstruction; zero later transport. |
| LR2 | 33 malformed ordinary outcomes passed; success, receipted timeout/error/missing, and explicit unreceipted failure regressions passed. **Two control-flow exception cases BLOCKED.** |
| LR3 | Not executed: mandatory P2 stop. |
| I1 | Verification/report locks inspected; full independent regression not reached. No lock relaxed. |
| I2 | LR1/LR2 catch/restart retention exercised; control-flow exception continuation fails. Separate skip/duplicate/prompt/manifest cases not reached. |
| I3 | Full A/B completion and mixed/allfail replay not reached. |
| I4 | Malformed checkpoint/transport boundaries exercised; dedicated resealed journal/lineage attacks not reached. |
| I5 | Authorization boundary inspected; independent grant regressions not reached. |
| I6 | Actual protected-file hashes captured and loader verification completed; eight planned byte-mutation attacks and independent projection recomputation not reached. |

**Counts And Limitations**
75 distinct attack cases plus five valid regressions: **80 distinct cases**, 81 executions including one repeated malformed-transport case after correcting an overly strict temporary-probe assertion. There were 44 synthetic transport invocations, including seed/control continuation calls, and 698 passing assertions. [Exact counts](/C:/Users/marcu/AppData/Local/Temp/G-EXTRACT1-independent-20261004-2a3bda95/stage1_counts.json).

The complete 1,447-file pilot comparisons/replays, report/schema binding checks, all64 subsets, all108 E5 audits, and elapsed/scorer/reserve/gate checks were **not completed because of the stop requirement**. Producer test counts are not independent scientific approval.

**Bindings And Preservation**
Verified checkout HEAD: `2a3bda951e7ae48802834712c38c9d6be1e27169`; branch `g-extract1/design`. Repair commit appears immediately below HEAD: `29d6d7897cac83c66c02ca96711325381937b8db`.

Candidate SHA256: `687a9a50d9bbbe480f3e74e103f5b75c621a46a9ffdcc8e80dab65f6b2915a35`.
Runner SHA256: `5bfcab71a8eef4986da971f542a73d1a8c759ed8ab5a396849964afce6ab2100`.
Manifest SHA256: `aad9f460edd373f5ce3a0b5469449e4b6df918081c956ca819c1b515f8ca1042`.

[Before hashes](/C:/Users/marcu/AppData/Local/Temp/G-EXTRACT1-independent-20261004-2a3bda95/before_hashes.json) and [after hashes](/C:/Users/marcu/AppData/Local/Temp/G-EXTRACT1-independent-20261004-2a3bda95/after_stage1_hashes.json) contain all seven source hashes and all50 protected-file hashes. **All60 monitored files matched before/after**, including all corpus JSON and both superseded candidates with the specified digests. Repository status remained unchanged, including the seven intentionally untracked files.

Accepted closure remained `6c85b10930cefe410a1965c0924e4fd9f47eb4ef`. Zero socket-tripwire attempts; no provider/model/metadata contact, real A/B, actual grants, activation, commits, or repository edits.

