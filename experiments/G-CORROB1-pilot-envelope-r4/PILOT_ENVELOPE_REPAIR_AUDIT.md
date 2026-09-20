# G-CORROB1 Mechanical Pilot Envelope Repair Audit

Date: 2026-09-19

Verdict target: operator review before any mechanical-pilot retry.

## Preserved historical result

The first authorized live pilot remains `MECHANICAL PILOT REQUIRES REPAIR`.
It made one A call, then stopped on `empty_response`; B, pairing, scoring, and
the production experiment did not run.  Its runtime directory and receipts are
not modified or reinterpreted by this repair.  The prior pilot-capable candidate
also remains byte-preserved.

## Root cause

The adapter selected only `payload["response"]` and discarded the rest of the
Ollama response envelope before persistence.  That data-loss defect is
confirmed.  The original envelope was not preserved, so whether the 112
generated tokens appeared in documented `thinking`, another field, or no
usable field remains unknowable from the failed record.  The repair therefore
does not assert a post-hoc semantic answer.

## Repair

- Preserve exact response-body bytes and the complete decoded envelope.
- Persist an append-only raw envelope record before semantic processing.
- Apply one deterministic, fail-closed extraction policy.
- Persist raw envelope, extracted text, extraction metadata, parse result,
  validation, and governance as distinct evidence.
- Reuse the same adapter in pilot and production paths.
- Keep production semantic policy and fixed denominators unchanged.
- Add operational-only Activity extraction events.

## Safety review

No provider generation is allowed by this candidate. Pilot, provider-contact,
execution, and full-experiment authorization remain false. Belief effects
remain none. The candidate binds the existing corpus, gold, prompt, semantic
policy, comparator, scorer, and G-EVID1 policy without changing them.

## Remaining limitation

The next live pilot is still required to reveal the actual Ollama envelope for
this model/configuration. Ollama documents submitted options but does not
attest internally honored sampling behavior. No semantic interpretation of a
future pilot response is permitted.
