# G-CORROB1-R2 Authorized Execution Capability Implementation Audit

Verdict: READY FOR OPERATOR REVIEW BEFORE EIDOLON-INITIATED EXECUTION

This audit covers the narrow conversational capability only. It grants no execution authorization and records no
model observation. The production experiment, G-EVID1, corpus, gold, prompt, policy, comparator, scorer, thresholds,
sampling, and provider configuration were not semantically revised.

## Architecture trace

operator-created runtime authorization
-> exact `G-CORROB1-R2` chat command
-> fixed capability registry/matcher
-> current candidate rebuild and artifact-drift verification
-> exact authorization schema, scope, time, denominator, model, and manifest verification
-> exclusive one-shot authorization consumption
-> existing provider preflight
-> existing production runner
-> existing parsing, validation, governance, pairing, scorer, persistence, and Activity
-> content-minimized terminal receipt/reference
-> stop

The public execution function accepts only `manifest_id`. Runtime-root, provider, Activity, and cancellation injection
exist only on private test/integration helpers and cannot be supplied through the chat command.

## Requirement matrix

| Requirement | Implementation | Deterministic proof | Status |
| --- | --- | --- | --- |
| Exact manifest only | anchored command matcher plus fixed `MANIFEST_ID` | alternate ids, paths, and override text rejected | PASS |
| Separate operator authority | runtime-only authorization artifact; no creator function | missing/malformed authority rejected before provider inspection | PASS |
| Exact freeze binding | candidate rebuild plus full artifact digest map | corpus/config/manifest mutation rejected | PASS |
| Full-experiment flag | exact authorization schema requires true | absent flag rejected | PASS |
| One execution only | exclusive consumption file before provider inspection | replay and concurrent duplicate tests | PASS |
| Success/failure/incomplete/cancel consume | same pre-provider burn boundary | terminal-state matrix tests | PASS |
| No retry | existing runner/provider contracts unchanged | historical implementation/provider tests | PASS |
| No chat overrides | public function has one argument; exact schema rejects extras | signature and extra-field tests | PASS |
| Existing scientific path reused | production runner remains semantic owner | 192-call deterministic fixture regression | PASS |
| A/B blindness preserved | request builder unchanged | historical blind-request tests | PASS |
| Operational-only Activity | existing adapter reused; failure is observational | Activity content/invariance regressions | PASS |
| Safe terminal projection | run id, state, reason code, receipt, call count only | forbidden semantic/evaluation term test | PASS |
| Namespace isolation | fixed production run root and separate auth/receipt roots | no path accepted from chat | PASS |
| Belief effects | hard-coded `none` in candidate, authorization, consumption, and receipt | tamper tests | PASS |
| G-EVID1 integrity | no G-EVID1 file in diff | source diff inspection and historical guards | PASS |

## Known failure mode matrix

| Failure mode | Expected behavior | Observed deterministic behavior |
| --- | --- | --- |
| missing authorization | refuse before provider inspection | PASS |
| malformed authorization | refuse before provider inspection | PASS |
| stale authorization | refuse | PASS |
| consumed authorization | refuse; no retry | PASS |
| multiple unconsumed authorizations | refuse ambiguity | PASS |
| concurrent duplicate request | exactly one reaches runner | PASS |
| manifest/artifact drift | refuse before provider inspection | PASS |
| provider/model/options mismatch | existing runner preflight fails closed | PASS |
| failed run | persist terminal failure; authority remains consumed | PASS |
| incomplete run | persist incomplete terminal; authority remains consumed | PASS |
| cancelled run | stop between calls; persist cancelled terminal; authority remains consumed | PASS |
| Activity failure | scientific execution unchanged | PASS |
| attempted chat path/config override | command does not match | PASS |

## Test evidence

- New capability suite: 12/12 passed.
- Existing G-CORROB1 implementation, freeze, pilot, provider-envelope, and renewed-gold suites: 74/74 passed.
- Targeted Python compile: passed.
- Provider/model calls during implementation and audit: 0.
- Pilot launches: 0.
- Full-experiment launches: 0.

## Limitations

- Cancellation is observed between generation calls. The current synchronous Ollama request must return or time out
  before the cancellation signal can stop the next call.
- Ollama still does not attest that every submitted generation option is honored internally; the frozen provider
  contract preserves this known limitation.
- The candidate is non-authorizing. A separately generated and operator-approved exact authorization artifact remains
  mandatory before Eidolon can invoke the full run.
- Experimental interpretation remains a separate review task; no result is adopted into beliefs automatically.

No live provider request, pilot, production observation, belief update, installation, or release action occurred.
