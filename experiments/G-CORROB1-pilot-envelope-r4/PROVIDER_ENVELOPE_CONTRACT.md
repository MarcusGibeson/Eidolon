# G-CORROB1 Provider Envelope Contract

Status: candidate, not authorized for provider contact or execution.

## Provider representation

The Ollama `/api/generate` non-streaming response body is preserved as exact
HTTP entity-body bytes encoded with base64 and bound by SHA-256.  The decoded
JSON object is also preserved in full and separately bound by a canonical JSON
digest.  Exact body bytes are authoritative if later extraction code changes.

Ollama 0.34.0's documented `GenerateResponse` has two text-bearing fields:

- `response`: generated final response;
- `thinking`: separately emitted thinking text when thinking is enabled.

No undocumented field is eligible for semantic-output extraction.

## Extraction policy

1. A non-empty text `response` is the primary output.
2. Empty strings and whitespace-only strings are unpopulated.
3. A lone non-empty `thinking` value is eligible only when it parses as one
   complete JSON object. Arbitrary thinking prose is not promoted.
4. If both fields are populated, they must be identical after trimming outer
   whitespace. Identical fields select `response`; different fields fail closed.
5. A non-text value in either documented field fails closed.
6. No populated eligible field fails closed.
7. Extraction status, method, selected field, field digests, reasons, and the
   extracted text are sealed by an extraction digest.

The policy does not alter the semantic schema, structural validator,
individual governance, paired comparator, scorer, gold, thresholds, corpus,
or production denominators.

## Persistence order

Each returned body is written first to a distinct append-only
`provider_envelopes/<call_id>.json` record.  The later assessment record copies
the immutable envelope evidence, stores the extracted model output separately,
and links the first record by digest.  Pilot records remain under the pilot-only
namespace and cannot certify a production result.

Activity may report response receipt and extraction success/failure counts. It
does not expose envelope content, extracted text, semantic fields,
dispositions, gold, or safety labels.
