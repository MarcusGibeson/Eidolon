# G-ROUTE4 O2 amendment (post-seal, pre-contact), 2026-09-29

**Decision.** The operator amends the O2 adjudicator request settings before any adjudicator contact. The model
(`claude-opus-5-5`) and channel (Anthropic Messages API) are unchanged.

**Why.** Anthropic's published API contract for `claude-opus-5-5`, checked on 2026-09-29, makes two sealed request
parameters invalid. Every request carrying either would be rejected with HTTP 400:

- `thinking: disabled`: adaptive thinking is always on for this model and cannot be turned off.
- `temperature: 0`: non-default sampling values are rejected on every request.

The sealed output limit (2,048 tokens) would also defeat its own stated purpose, because on this model the limit
counts thinking as well as the reply. The evidence (pages and findings) is recorded in
`adjudicator_config_amended.json` under `provider_documentation_evidence`.

**What is preserved.** The sealed configuration `experiments/G-ROUTE4-candidate/sealed/adjudicator_config.json`
(sha256 `1658b9a2a32fa176c8ca679d5407725b17379902610869fc3cdc91d03df88029`) is unchanged and remains the historical
frozen configuration. The seal commit `50e6b46994299ffd71c97aa3f81f30637efaba1c` and the audit-sample commit
`29f5a477693d703699af62f9fc0e0945c9c66be2` are not modified. The prompt template, input rendering, blindness,
fresh-session, no-tools, retry, parse-failure and judgement rules carry over byte-for-byte.

**Amended request settings.**

| Setting | Sealed | Amended |
|---|---|---|
| Model / channel | `claude-opus-5-5` / Messages API | unchanged |
| Thinking | disabled | omitted (adaptive, provider-required) |
| Temperature | 0 | omitted (provider default) |
| Effort | not set | `high`, explicitly frozen (`output_config.effort`) |
| Maximum output tokens | 2,048 | 32,000 |
| Tools | none | none (no tools field) |
| Server-side fallback | not addressed | disabled: no `fallbacks` field, no beta header; a response naming another model or reporting a fallback is an integrity stop |

**Binding answer.** The binding answer is the concatenated text content of the first final assistant message
returned for the adjudicator slot. A refusal, malformed final answer or truncated final answer still binds and is
scored under the frozen procedure. The only retry is the frozen single retry of a no-answer (a session error with no
final message); an answer is never retried because it is unusable, surprising or disagrees with gold.

**Scope of the change.** O2 permits a change by recorded operator decision, after which every fixture is
re-adjudicated from scratch. No adjudication session has taken place, so no fixture needs re-adjudication. The
design's rule that nothing changes after provider contact is not engaged: this amendment precedes any contact.

**Binding.** The amended configuration is `adjudicator_config_amended.json`, derived deterministically from the
sealed configuration by `o2_amendment.py`, with digest
`7691126e6a96974d43f816ee61253332ba5b2510395de2baa8fdd7342581d516`. Every adjudication request and result records
that digest.

**Historical disclosure (added 2026-09-29, operator ruling on corpus-review finding B3).** In the A′ batch `g4adj-amain-20260929T180225Z`, the single HTTP 400 billing rejection (A4-PLAN-R1-03 slot 3, invocation 1) was classified by explicit operator ruling as a no-answer (journal seq 214–215), despite the literal wording of the amended classification rule (any other 400 is `request_rejected`: the batch stops, not retried); its single frozen retry bound. The resumed run segment used harness commit `f0c441087d00ad64a98fb26f67dd04fa5a804907`, not the `run_start` harness commit `160dea16e39d64ddb4382840dfbb87c8cd0772a7`. The historical result is not reinterpreted or re-run.
