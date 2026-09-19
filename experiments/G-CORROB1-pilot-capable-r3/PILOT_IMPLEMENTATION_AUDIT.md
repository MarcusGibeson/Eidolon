# G-CORROB1 pilot-capable implementation audit

**Verdict:** `READY FOR OPERATOR REVIEW BEFORE LIVE MECHANICAL PILOT`

**Base checkpoint:** `1d840379e7177968c1f744a49989d51f95453823`

**Provider generation calls during implementation/audit:** `0`

**Live pilot launches:** `0`

**Full experiment launches:** `0`

## Architecture

The new path is additive. It does not edit the historical R2 candidate, the
192-call production runner, the production scorer, production policy, corpus,
gold, prompt, thresholds, or G-EVID1.

The two-call pilot uses `PX01`, an explicitly synthetic identity outside the
32-item corpus. It reuses production request construction, generation options,
Ollama adapter, parsing, structural validation, individual governance, paired
comparison, append-only call/pair persistence, and shared Activity core.

Pilot-only code supplies authorization consumption, a namespaced runner,
content-minimized Activity projection, mechanical lineage verification, a
terminal sealing receipt, and the pilot-capable freeze. No gold is loaded and no
semantic correctness, safety, utility, agreement, or disposition result is
evaluated.

## Requirement-to-proof matrix

| Design requirement | Implementation | Deterministic proof | Status |
|---|---|---|---|
| Exactly one A/B pair | `PILOT_FIXTURE.json`, `g_corrob1_live_pilot.py` | authorized fixture records exactly 2 calls / 1 pair | pass |
| No authority, no contact | `verify_pilot_authorization` precedes adapter inspection | absent/tampered authorization leaves inspection and generation counts at zero | pass |
| One-shot pilot authority | exclusive authorization-consumption receipt | reuse fails before a second provider generation | pass |
| Full execution remains denied | candidate and wrapper require `experiment_authorized=false` | authority escalation mutations rejected | pass |
| Production components reused | production imports in live harness | end-to-end fixtures traverse request, policy, comparator and persistence | pass |
| Production scorer unchanged | `g_corrob1_scorer.py` unchanged | pilot 2/1 units rejected; production still requires 192/96 | pass |
| Pilot cannot certify production | pilot verifier has no gold and emits `production_result=false` | completed pilot retains `valid_verdict=false` | pass |
| Production cannot certify pilot | fixed production denominator | scorer rejection test | pass |
| Blind A/B isolation | minimal production request body; no prior response passed | request-body equality and forbidden-field tests | pass |
| Fail-closed provider binding | preflight plus per-request digest/model checks | wrong model, digest, options and fallback rejected | pass |
| Fail-closed assessment mechanics | production structural validator | malformed, truncated, wrong-bound and cross-contaminated outputs abort | pass |
| Namespaced persistence | `g_corrob1_mechanical_pilot/<run-id>` and pilot flags on every record | namespace/result-boundary checks | pass |
| Complete lineage | raw call records, pair, pilot report, terminal receipt | digests recomputed and lineage reconstructed | pass |
| Activity is operational only | `g_corrob1_pilot_activity.py` allowlist | snapshot leakage scan and telemetry on/off parity | pass |
| Historical production freeze preserved | freeze builder verifies all old artifact digests | drift in any historical artifact blocks candidate rebuild | pass |

## Known-failure-mode matrix

| Failure mode | Test | Required behavior | Observed |
|---|---|---|---|
| Missing pilot authority | absent authorization | zero provider inspection/generation | pass |
| Reused authority | one-shot authorization reused | reject before another generation | pass |
| Model/config/fallback mismatch | adversarial preflight receipts | zero generation, incomplete terminal receipt | pass |
| Malformed/truncated output | adversarial raw/metrics | preserve first response, abort, no retry | pass |
| Wrong binding/assessor | swapped ID, digest, proposition, cross payload | structural/provenance rejection | pass |
| Missing/duplicate role or pair | verifier mutations | mechanical result rejected | pass |
| Provider interruption | B transport failure | preserve both attempts, no pair, no retry | pass |
| Stale run | duplicate run identity | fail before another generation | pass |
| Record digest drift | call-record mutation | lineage rejected | pass |
| Activity failure | throwing observer | scientific/mechanical records unchanged | pass |
| Activity disclosure | snapshot scan | no item, assessment, disposition, gold or safety content | pass |
| Namespace crossover | production/pilot scorer cross-tests | neither path certifies the other | pass |

## Deterministic verification

- Pilot-specific adversarial suite: `21/21` passed.
- Existing G-CORROB1 implementation suite: `28/28` passed.
- Existing pre-pilot gold-signoff suite: `5/5` passed.
- Existing execution-freeze suite: `7/7` passed.
- Historical G-EVID1 contract suite: `1966/1966` passed.
- Provider generation calls: `0`.

The final compile, freeze rebuild, exact candidate verification, and source-diff
integrity checks are performed after this audit text is sealed because this file
is itself a behaviorally bound freeze artifact.

## Remaining limitations

- Ollama accepts the submitted options but does not attest their internal use.
- Distinct seeds and fresh sessions are mechanically submitted; sampling
  independence is not established.
- The authorized live pilot is still required to observe actual request/response
  mechanics and seed behavior without interpreting semantics.
- Native Tcl/Tk Activity rendering remains an environment limitation; shared
  Activity contract/API behavior is deterministically verified.

No pilot authority or full-experiment authority is granted by this audit.
