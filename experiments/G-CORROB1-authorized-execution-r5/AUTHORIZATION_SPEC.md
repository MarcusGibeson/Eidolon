# G-CORROB1-R2 Authorized Execution Capability

Status: implementation candidate only. No execution authorization is contained in source.

## Fixed capability

The conversational surface accepts exactly:

`Execute authorized frozen experiment G-CORROB1-R2.`

The conversation supplies only the registered manifest identifier. It cannot supply a file path, provider, model,
prompt, corpus, gold, seed, option, retry instruction, or policy override.

The capability resolves one authorization artifact from the runtime-only directory
`experiment_execution_authorizations/G-CORROB1-R2/`. Zero or more than one artifact fails closed.

## Separate operator authorization

The capability cannot create, approve, revise, or renew an authorization. A valid runtime artifact has contract
`g-corrob1.r2.operator-execution-authorization.1` and is bound to:

- the exact `G-CORROB1-R2` manifest identifier;
- one exact authorized execution-manifest digest;
- one fixed scope, `one_frozen_g_corrob1_r2_execution`;
- 192 generation calls and 96 A/B pairs;
- the frozen provider/model/configuration contract;
- one validity interval;
- an explicit `execution_frozen = true` assertion;
- one explicit operator confirmation;
- `belief_effects = none`.

Extra fields fail closed. No conversational text can override a field.

## One-shot consumption

After the artifact and installed freeze verify, an exclusive consumption record is created before provider inspection
or generation. The same authorization cannot be used by a second request, concurrent request, retry, cancellation,
failed run, or incomplete run. A new operator artifact is required for every later attempt.

Invalid, stale, missing, ambiguous, or drifted artifacts grant no authority and cause no provider contact.

## Delegation and output

The capability delegates to the frozen production runner, provider adapter, structural validator, governance,
comparator, scorer, append-only run store, and shared Activity adapter. It does not implement alternate experiment
semantics.

Conversation receives only manifest id, run id, terminal state/reason code, terminal receipt reference/digest, and
provider-call count. It receives no corpus text, semantic output, disposition, gold, safety label, score, or verdict.
Interpretation remains a separate review task.

## Authority excluded

This capability grants no authority to create or edit experiments, manifests, corpus, gold, prompts, configuration,
seeds, governance, comparator, scorer, source, installation, release, beliefs, retries, or follow-on experiments.
