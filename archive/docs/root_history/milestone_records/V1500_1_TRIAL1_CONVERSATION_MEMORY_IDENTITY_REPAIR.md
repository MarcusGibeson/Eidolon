# v1500.1 Trial 1 Conversation Memory and Identity Repair

## Observed failures

- A direct question about Eidolon's progress inherited the prior rest-and-recharge frame and repeated it.
- An explicit request to remember Melissa was not available to later turns in the same conversation.
- Marcus and Melissa were assigned to the wrong identity roles after correction.
- A local recommendation named a place without current lookup evidence.

## Repair

- Resolve a small allowlist of user-authored active facts before provider generation.
- Persist only explicit personal-memory requests through the existing relationship curation store.
- Reuse those explicit active records after restart, while rejecting assistant-authored and ineligible memory text.
- Apply newest user corrections before older facts.
- Answer direct self-progress questions and stale-frame corrections through bounded grounded responses.
- State the local-information limitation instead of inventing current places or events.

## Verification

- `tools/v1500_1_conversation_memory_identity_repair_tests.py`: 19/19.
- Retained relationship and responsiveness suites: 27/27.
- Retained Trial 2, Trial 3, correction/recall, and relationship/preference suites: 211/211.

Automated evidence does not replace the next unscripted operator conversation trial.
