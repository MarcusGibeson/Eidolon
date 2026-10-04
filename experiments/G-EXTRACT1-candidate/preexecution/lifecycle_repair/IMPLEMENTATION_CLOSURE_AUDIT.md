**Overall: BLOCKED**
Exactly one independent read-only audit of `a861c5676a1254ff99f6a7df55e11824c652e948`. **Parent must STOP.** No repair or further review was performed.

**Blocking Findings**
1. **P1: Malformed checkpoints do not remain terminal.** A correctly hashed checkpoint with payload `[]`, `null`, integer, or string raises `AttributeError` at [g_extract1_journal.py:96](/C:/Users/marcu/Eidolon-g4adj/tools/g_extract1_journal.py:96). The [guard at line 90](/C:/Users/marcu/Eidolon-g4adj/tools/g_extract1_runner.py:90) does not retain it. After catching the exception, all four attacks successfully resumed using the original checkpoint and invoked the next synthetic transport once. Integrity events before retry: `[]`.

2. **P1: Malformed transport results allow continuation.** A synthetic transport returning `None` raises an unretained `AttributeError` at [g_extract1_runner.py:331](/C:/Users/marcu/Eidolon-g4adj/tools/g_extract1_runner.py:331), after recording `START`. Catching it permits the next scheduled call to execute, leaving an unreceipted omission in the journal. Retained events: `[]`; subsequent transport invocations: `1`.

3. **P2: Pre-contact blocked cells remain scheduled.** An actual harness call with mismatched identity receipts produces `PRE_MODEL_IDENTITY_MISMATCH`, zero transport calls, and verdict `PRE_CONTACT_BLOCKED`, but all six cells remain `A_SCHEDULED`. [g_extract1_runner.py:225](/C:/Users/marcu/Eidolon-g4adj/tools/g_extract1_runner.py:225) never applies the frozen `A_BLOCKED` transition.

**I1–I6 Results**
| Item | Independent Result |
|---|---|
| I1 | Ordinary unverified `perform`, `enter_b`, `checkpoint`, and `final_report` reject with zero transport calls. Malformed-checkpoint terminal semantics remain blocked by finding 1. |
| I2 | Skip/retry errors survive catching and reconstruction; sealed interruption remains `INCOMPLETE` and prevents A qualification. Findings 1–2 defeat complete terminal retention. |
| I3 | Actual 480-observation A completion correctly derives six eligible cells before B entry. Zero/mixed A, `B_NOT_ELIGIBLE`, isolated receipted A/B failures, and B-invalid reporting passed. Finding 3 remains. |
| I4 | Seven resealed FAILURE mutations rejected. Fabricated START lineage, checkpoint seal, and missing marker target rejected; prefix, position, schedule, and binding mutations rejected. Malformed checkpoint shape remains defective. |
| I5 | Mechanical `exercise_authorization=True`: B-only grant resumed B successfully; A-for-B and candidate-freeze grants rejected. No real grants or activation. |
| I6 | Independently enumerated manifest maps/scalar bindings and hashed all 50 protected files. Candidate source bytes and separate gold projection verified. All 17 newly covered files rejected pre/post byte mutations; four named omissions additionally tested through `Run.perform`. |

**Core Verification**
- Schedules recomputed: **480 A / 240 maximum B / 720 maximum**, all **64** conditional B subsets, all **720** request hashes.
- All **108 E5** selector-invariance entries recomputed; **12** elapsed clarifications preserved; scorer checked across every variant with exact, malformed, and wrong-value outputs.
- Both complete pilot trees independently replayed and compared: **1,447 files each, byte-identical**, matching recorded file hashes. Targeted journal/incident chains independently hashed.
- Producer counts **2,153 / 130** were independently counted, not accepted as blanket proof.
- Fresh rehearsal completed **480 synthetic A + 159 synthetic B** observations before stopping promptly. Fresh B completion and all-failed/mixed-B rehearsals were not completed; no producer pilot rerun.

Verified schedule SHA-256:
```text
A: 3c48390307dd683e7ba2f736318d42f4d9fbda6527bbb9d64ee03b4bf97bb4dd
B: 6361e990216be94ca3ad69b75b485adf70fc8a035b2e459e5d309063c8ea164b
```

**Commands And Candidate**
Executed from `C:\Users\marcu\Eidolon-g4adj`:
```powershell
python -B -X utf8 C:\Users\marcu\AppData\Local\Temp\gextract1-final-a861-audit\audit.py
python -B -X utf8 C:\Users\marcu\AppData\Local\Temp\gextract1-final-a861-audit\supplement.py
```
Main rehearsal deliberately stopped after established blockers; supplement exited `0`. Both used socket tripwires and repository-write guards.

Verified new candidate SHA-256:
`6e7295b3c79ee95930fee7231265e342905b7848d261ae716d1ef1546ca785ab`

Source, accepted-package, schema, schedule, and report bindings match. Explicit supersession of retained blocked candidate `14fb601c3a58777942ccd0361c2a303b5bfcf10d4c05536a32d265c0babe537f` verified.

**Governance**
Provider/model calls, network attempts, and real A/B calls: **0**. No activation, real authorization, commits, or repository edits. All 50 protected files and seven untracked corpus files remain unchanged. Science unchanged; G-ROUTE4 unchanged; autonomy false; belief effects none. Findings returned here for the parent to record unchanged.

`G_EXTRACT1_LIFECYCLE_REPAIR_FAILED`
