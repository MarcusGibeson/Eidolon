# G-CORROB1-R2 stopping and abort rules

**Status:** preregistered design behavior; no runner or pilot exists yet.

## Individual assessment defects that do not by themselves abort a complete run

- Malformed model output, truncation, binding failure, forbidden authority field,
  or quote-grounding failure is preserved as the scheduled call's sole result.
- It is structurally invalid, receives operational `abstain` through G0, and adds
  a distinct scientific `structural_rejection` status.
- No JSON-repair call, retry, replacement response, or manual correction occurs.
- The run may continue only when the provider call returned and the defective
  record, raw observable output, contact accounting, and failure reason were
  durably preserved.

## Infrastructure-incomplete aborts

Abort the run, preserve all prior records, and prohibit pass/fail scientific gates
when any of the following occurs:

- a scheduled assessment is missing because of transport/process/provider failure;
- provider or exact model identity differs from the execution manifest;
- any requested sampling/configuration field is unsupported, ignored, or changed;
- an unexpected retry or unaccounted provider contact occurs;
- frozen artifact, prompt, schedule, model, configuration, provenance, source, or
  mutation-guard digest mismatches;
- a scientific record cannot be durably written or bound to its scheduled call;
- provider contact occurs after the run should have stopped;
- runner/comparison/scorer self-tests do not pass before first provider contact.

An incomplete run cannot be resumed or replayed under the old authorization.

## Mechanical pilot failure

A future structural pilot must use deterministic stubs and unrelated synthetic
fixtures only. Any mismatch in rendering, validation, rule replay, comparison,
scoring arithmetic, provider accounting, mutation guards, or Activity isolation is
a mechanical pilot failure. No scientific conclusion is drawn. Repair requires a
new implementation candidate, new hashes, and a new implementation audit before
another pilot. Pilot observations cannot tune semantic prompt, gold, sampling,
comparison, metrics, or gates.

## Scorer failure

A scorer self-test failure before contact blocks launch. A scorer defect discovered
after contact preserves the run but blocks its verdict. Repair produces a new
scorer/version and audit. Rescoring is permitted only under a prospectively
reviewed rule that does not change gold, metric meaning, or success criteria; both
the defective and corrected reports remain preserved.

## Activity instrumentation failure

Activity is observational and non-authoritative. A telemetry write/display failure
is nonfatal only if prompts, order, calls, timing contract, scientific persistence,
outputs, comparison, and scoring are unchanged; the scientific run records an
`activity_degraded` warning and Activity cannot claim live completeness. If
instrumentation changes or interrupts scientific behavior, the run is
infrastructure-incomplete and aborts.

## Contamination or gold defect after revision

- Discovered before provider contact: block launch, revise corpus/gold, create a
  new candidate, and repeat preregistration audit.
- Discovered after provider contact: preserve and mark the run compromised; do not
  edit gold, remove an offending item post hoc, or report the affected run as a
  confirmatory pass. The item cannot be reused as unseen validation.

## Semantic experimental failure

A complete run with any paired unsafe use, failed utility gate, correlated
false-clean agreement, poor semantic accuracy, or excessive conservatism is a
valid experimental result. It is not an infrastructure defect and does not permit
repair, threshold relaxation, gold revision, prompt tuning, or rerun under the
same confirmatory claim.
