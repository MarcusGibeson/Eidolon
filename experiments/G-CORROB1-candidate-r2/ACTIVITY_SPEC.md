# G-CORROB1-R2 Activity observability specification

**Status:** specification only; no Activity adapter or experiment runner exists.

The eventual adapter uses Activity v1 as disposable, content-minimized operational
telemetry. It grants no authority and is not scientific evidence.

## Allowed stages

1. `preflight_validation`
2. `assessment_collection`
3. `structural_validation`
4. `paired_comparison`
5. `scoring`
6. `finalization`

## Allowed identities and metrics

- candidate/run ID and execution-manifest digest;
- current phase and terminal state;
- items completed / 32;
- pairs completed / 96;
- A completed / 96 and B completed / 96;
- scheduled calls / 192, provider contacts, returned responses;
- validation completed / 192;
- structural-failure and grounding-failure counts;
- comparisons completed / 96;
- scoring units completed / fixed total;
- elapsed seconds and content-free warning codes.

## Forbidden telemetry

Activity must not contain proposition/evidence text, rendered prompts, model
outputs, quotes, semantic labels, confidence, individual or paired dispositions,
gold, expected answers, safety labels, item families, contamination labels,
scorer verdicts during collection, hidden reasoning, credentials, or arbitrary
exception text.

The semantic provider receives no Activity state. The scorer reads frozen
scientific records, not UI projections. Activity ordering cannot control call
ordering, retries, stopping, comparison, or scoring.

## Required future parity tests

- telemetry on/off produces byte-identical rendered prompts and equal ordered
  provider requests, outputs, validation, comparison, and scoring;
- telemetry persistence failure is nonfatal and content-free when scientific
  persistence remains intact;
- instrumentation cannot add retries or provider contacts;
- read-only Activity APIs do not mutate or resume a run;
- terminal Activity state follows authoritative scientific status and never turns
  an incomplete/failed experiment into a pass;
- no forbidden field appears in snapshots, events, web/mobile/desktop surfaces,
  logs, or API payloads.
