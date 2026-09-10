# Eidolon v2200.9 Desktop Tools, Research, Voice, and Multimodal Gate Ledger

Status: Desktop-reviewed source-only checkpoint; unpromoted and not installed.

## Input identity

- Candidate ZIP SHA-256: `37e190a46b6859690d7520b6b5d08842a79cbde7ea64516f52b6bd198a5e2042`.
- Authoritative v2100.9 baseline ZIP SHA-256: `0d2962924f81acbe53e093df9c9a9eed525450f40cf32251b9ce75c3439d8534`.
- Archive shape: one `Eidolon/` root; no packaged private runtime data, project registry, cache, bytecode, or Git metadata.
- The cumulative diff matched every declared path, change kind, and non-self-referential SHA-256: 14 added, 11 modified, 0 deleted.

## Windows and native evidence

- Repaired focused Era 7 suites: 107/107 passed.
- The Windows quick release verifier passed in 245.177 seconds before repair. After repair, the full release verifier passed in 312.899 seconds with valid evidence, zero source writes/deletes, source immutability, and external runtime separation.
- Disposable Windows file create, read, move, cleanup, and process inspection succeeded outside source.
- Live HTTPS retrieval and one-hop redirect handling succeeded with bounded response metadata and content digests.
- Windows reported two 1920x1080 displays, a 3840x1219 virtual desktop, 100% system DPI, and five sound devices in OK status.
- Configured Ollama readiness passed for `qwen2.5:7b` generation and `nomic-embed-text:latest` embeddings. Native generation, streaming, and 768-dimensional embedding smoke checks passed with matching configuration digest and no model management.

## Desktop repairs

1. Research downloads, extraction, and source observations now require self-consistent native receipt contracts; a caller-supplied `authoritative=True` flag is not evidence.
2. Visual region observations now require an exact digest-bound native observation receipt before they can support a visual claim.
3. Tool previews and integrated four-modality packets validate their component digests and reject empty, malformed, or tampered components.
4. Completed, cancelled, and failed voice turns are terminal and cannot be rewritten by a later event; turn IDs cannot be reused.
5. Malformed or nonfinite numeric values now fail closed across tool timeout, research size/quality, voice timing/confidence/prosody, and visual dimensions/confidence/bounds.

## Remaining limitations

- Era 7 adds governed contracts and state machines, not new native microphone, STT/TTS, OCR, screen-capture, clipboard, notification, or browser execution adapters.
- Device discovery proves Windows availability, not end-to-end audio intelligibility, first-audio latency, barge-in through hardware, or device-removal recovery.
- Display discovery proves current geometry and scale, not OCR quality, inaccessible-window behavior, or live multi-monitor capture because no capture adapter was authorized or introduced.
- Live network probing proves host HTTPS behavior, not that Eidolon can independently browse; research execution still requires a governed browser adapter and receipt binding.
- This gate is not installation, promotion, certification, model management, destructive operation, or independent authority.

## Next bounded unit

`v2201.0 - Fine-Grained Authority and Permissions Policy Model`
