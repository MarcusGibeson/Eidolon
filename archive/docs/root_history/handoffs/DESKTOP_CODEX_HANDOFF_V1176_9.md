# Desktop Codex Handoff: Eidolon v1176.9

## Candidate role

Source-only v1176.9 Clarification and Argument Routing Read-Only Checkpoint candidate.

This candidate is not final, installed, promoted, certified, release-authorized, or publish-safe.

The scheduled Desktop Codex and native-provider decision gate remains v1200. This handoff is bounded preparation for that later review, not a request to advance the review date.

## Review focus for Windows

1. Extract beneath exactly one `Eidolon/` root.
2. Confirm the supplied ZIP SHA-256 before extraction.
3. Confirm `conscious_agent/release_metadata.py` reports working source v1176.9 and previous source v1176.8.
4. Run external-cache compilation under Python 3.11.
5. Run:
   - `tools/v1176_0_2_bounded_action_argument_clarification_tests.py`
   - `tools/v1176_3_5_structured_clarification_proposal_binding_tests.py`
   - `tools/v1176_6_8_clarification_reliability_continuity_tests.py`
   - `tools/v1176_9_clarification_argument_routing_checkpoint_tests.py`
6. Invoke `python eidolon.py clarification-argument-routing-checkpoint`.
7. Verify the GET-only endpoint `/api/cognition/clarification-argument-routing-checkpoint`.
8. Confirm POST to that endpoint is rejected.
9. Confirm the dashboard panel reports Desktop review deferred to v1200.
10. Confirm the source tree remains byte-identical after checkpoint execution.

## Native-provider review boundary

No native provider call is required or authorized for this checkpoint. Ordinary conversation integration should be reviewed only for parity and non-execution:

- streaming and non-streaming both build the same bounded action projection;
- no conversation executor exists;
- no clarification continuity mutation is invoked by ordinary conversation;
- no action success may be claimed without an authoritative existing receipt;
- no prompt, conversation, memory, provider payload, raw argument, answer value, or private reasoning appears in diagnostics.

## Security and authority checks

Confirm that:

- traversal-like, absolute, and drive-qualified target references fail closed;
- only existing registered capability identifiers appear;
- clarification answers can fill only the originally requested allowlisted fields;
- stale, mismatched, replayed, duplicate, cancelled, expired, superseded, and malformed state fail closed;
- a clarified result creates only an unpersisted proposal candidate;
- no approval, authorization, execution, source mutation, model operation, installation, promotion, or certification is inferred.

## Known verifier debt

The quick profile is expected to remain blocked by inherited pre-v1175 fixtures that freeze retired metadata, UI, and recovery contracts. Current v1176.9 registration, performance budgets, cleanup, and source immutability pass. Do not repair unrelated historical fixtures merely to turn the aggregate profile green.

The v1165.9 and v1166.9 checkpoint wrappers also retain exact old release-identity assertions. Their underlying bundle suites pass.

## Stop condition

Stop after read-only review. Do not install, promote, certify, publish, continue into v1177, or move the Desktop Codex decision gate earlier than v1200.
