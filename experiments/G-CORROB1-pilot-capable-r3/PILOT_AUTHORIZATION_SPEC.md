# Mechanical-pilot authorization contract

A live pilot authorization must bind the exact pilot-capable freeze candidate and
contain all of the following:

- `pilot_authorized=true`
- `experiment_authorized=false`
- `provider_contact_authorized=true`
- the complete candidate manifest
- its canonical SHA-256
- exact operator confirmation:
  `Authorize G-CORROB1 live mechanical pilot <candidate-sha256>`

The candidate itself remains non-authoritative and stores
`pilot_authorized=false`. Authorization is a separate, one-shot input. Missing,
altered, stale, or mismatched authorization is rejected before model inspection
or generation.

The pilot expects exactly two generation calls and one pair. It cannot expand its
schedule, retry, invoke output repair, certify a production result, or grant full
experiment authority.
