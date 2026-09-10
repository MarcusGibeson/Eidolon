# v1500.8 Conversational Target Continuity Checkpoint

This unpromoted checkpoint keeps Eidolon's reply aimed at the newest user message and adds bounded repetition resistance to ordinary casual conversation.

## Behavior

- A current question, correction, or explicit topic shift outranks older requests.
- Short follow-ups such as `Why?`, `How so?`, and `Explain further` attach only to the latest completed user-assistant pair.
- Failed, cancelled, stale, and incomplete turns do not become continuity evidence.
- Exact and strongly paraphrased recent answers are replaced with a direct recovery statement.
- Repeated sentences are removed when the response still contains useful new material.
- The gate does not add a provider request and does not modify governed non-casual action responses.

## Verification

```powershell
python tools/v1500_8_conversation_target_continuity_tests.py
python tools/v1500_7_natural_association_coherence_tests.py
python tools/verification_compile.py --json
```

Native conversation and operator daily-use review remain required before promotion or installation.
