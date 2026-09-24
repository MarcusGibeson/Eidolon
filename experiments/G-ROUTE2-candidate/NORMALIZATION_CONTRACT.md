# G-ROUTE2 transport normalization contract

Contract: `g-route2.transport-normalization.v1`
Implementation: `tools/g_route2_normalization.py`

This layer is **transport canonicalization**, not repair. It removes one kind of wrapper and
nothing else. It is deliberately narrow, model-agnostic, and applied identically to the 7B, the
14B and the 27B.

## The rule

For JSON-profile tasks (`extraction.v1`, `research.v1`, `synthesis.v1`, `coding.v1`, `planning.v1`),
exactly two shapes canonicalize:

1. **raw** — the output, stripped of surrounding whitespace only, is exactly one JSON value and
   nothing follows it;
2. **one fenced block** — the output is exactly one markdown fence, tagged `json` or untagged,
   containing exactly one JSON value, with nothing but whitespace outside it.

Everything else fails closed and reaches structural validation exactly as the model wrote it.

`conversation.v1` is plain text and is never normalized.

## What is never permitted

Explanatory prose before or after the object; more than one fenced block; more than one JSON value;
malformed JSON; comments; truncated or completed JSON; a fence tag other than `json`; nested or
unbalanced fences; any rewriting beyond removing the two delimiter lines.

## Recorded outcomes

| Outcome | Meaning | Canonicalized |
|---|---|---|
| `raw_valid` | one JSON value, no wrapper | yes, unchanged |
| `fence_removed` | exactly one fenced JSON value | yes |
| `trailing_text` | non-whitespace outside the payload or the fence | no |
| `multiple_payloads` | two or more fenced blocks, or two or more JSON values | no |
| `invalid_json` | nothing parses | no |
| `wrapper_rejected` | unterminated fence, unsupported tag, ambiguous fence structure | no |
| `not_applicable` | text profile | n/a |

Every record keeps the original bytes in `raw_output`, both digests, an explicit `normalized`
boolean, and the name of the wrapper removed. Provenance is never discarded.

## Root type is a structural question, not a transport one

A JSON array or scalar canonicalizes successfully and is then rejected downstream with
`json_root_not_object`. Keeping root-type judgment out of the transport layer is what stops
normalization outcomes from smuggling in structural or semantic opinions.

## Semantic-value preservation

Canonicalization strips two delimiter lines. The payload is the fence body with surrounding
whitespace removed, and the layer refuses the output if `json.loads(payload)` is not equal to the
value parsed from the fence body. No field is added, removed, reordered in meaning, retyped or
edited, and no value is ever synthesized.

This is asserted three ways:

* **by construction** — the only transformation is delimiter removal;
* **by test** — `semantic_values_preserved` is checked on every adversarial case, including a
  pretty-printed body whose canonical form differs textually but parses identically;
* **by replay** — all 216 frozen G-ROUTE1 raw records were re-normalized, and on every one of them
  the parsed value was unchanged, no raw output was altered, and no judged semantic failure became a
  pass.

## Determinism

The layer is a pure function of the output text and the validator profile. It uses no clock, no
randomness and no external state, and the adversarial suite asserts that repeated calls return
byte-identical records.

## Why it is not called repair

Repair changes what the model said. This changes only how the model wrapped it. If the model said
something malformed, it stays malformed and it fails.
