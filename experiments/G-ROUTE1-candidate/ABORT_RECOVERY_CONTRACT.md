# G-ROUTE1 Abort and Recovery Contract

Status: implementation candidate; no provider generation authority.

## Scientific output failures

Malformed JSON, wrong answers, refusal, grounding errors, and validator rejection are preserved as model-produced scientific observations. They receive no repair call and do not by themselves invalidate the benchmark run.

## Infrastructure and provenance failures

The run stops incomplete on model absence, model or configuration drift, provider fallback, transport/process failure, schedule corruption, persistence failure, scorer denominator failure, checkpoint corruption, guarded dependency drift, duplicate records, or an unexpected restart that cannot prove exact continuity. Missing scientific outputs are never invented.

## Pause and resume

Pause is honored only between calls. The current completed count and exact next schedule position are digest-bound. Resume revalidates the fixture freeze, model/config receipts, schedule, append-only records, checkpoint, and mutation guard before the next call. A call interrupted after provider contact but before durable persistence makes the run incomplete; it is not silently retried. Provider memory release is provider-managed because no portable Ollama unload attestation exists.

One run lease prevents simultaneous writers. Activity displays cumulative completed work; the shared Activity clock excludes intentional paused time from active elapsed time. Activity content remains operational only.

## Authority

No retry, semantic repair, source mutation, belief effect, production route, automatic escalation, model install, or provider switch is authorized by this contract.
