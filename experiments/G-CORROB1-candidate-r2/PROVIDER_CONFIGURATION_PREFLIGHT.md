# G-CORROB1-R2 provider and configuration preflight

**Result:** metadata identity is compatible; semantic generation calls: `0`.

Ollama `0.34.0` resolves the requested alias `qwen3.8:27b` to local manifest
SHA-256 `22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643`.
The API tag, `ollama list` short ID `22130167c4c2`, and on-disk manifest digest
agree. The manifest binds model blob
`f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d`
and projector blob
`ac3714bfdddeca31351f2752bf1a63f266f4df87c0b68c895e44945ca704448e`.

## Configuration assessment

| Setting | Required | Status |
|---|---:|---|
| model | `qwen3.8:27b` | Verified by local manifest and `/api/tags`; no fallback observed. |
| temperature | `0.6` | Verified submitted; provider does not attest honoring. |
| top_p | `0.9` | Verified submitted; provider does not attest honoring. |
| top_k | `40` | Verified submitted; provider does not attest honoring. |
| min_p | `0` | Verified submitted; provider does not attest honoring. |
| repeat_penalty | `1.0` | Verified submitted; provider does not attest honoring. |
| context | `8192` | Submitted as `num_ctx`; provider does not attest honoring. |
| output cap | `350` | Submitted as `num_predict`; provider does not attest honoring. |
| stop | empty | Verified submitted; provider does not attest honoring. |
| stream | false | Verified in request body/config; provider does not attest internal behavior beyond non-stream response protocol. |
| seed | deterministic per call | Client submission path exists; behavior remains unknown until an authorized mechanical pilot. |
| fresh session | every call | New HTTP session and no conversation reuse are client-enforced; runtime behavior is not yet piloted. |
| retries | none | Client-enforced. |
| fallback | forbidden | Current alias resolves exactly; returned-model mismatch fails closed in the adapter. |

Installed defaults are temperature `1`, top-p `0.95`, top-k `20`, min-p `0`,
and repeat penalty `1`. These defaults do not conflict with the experiment
because every experimental request explicitly submits its frozen overrides, but
their presence makes the later request-capture pilot important.

Five successful metadata queries were made across the CLI/API inspection. No
prompt was submitted, no text was generated, and no semantic observation was
collected. Ollama supplies no per-option honoring attestation; this remains an
explicit pre-pilot limitation rather than being promoted to a verified claim.
