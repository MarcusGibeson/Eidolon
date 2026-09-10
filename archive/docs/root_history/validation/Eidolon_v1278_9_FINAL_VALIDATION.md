# Eidolon v1278.9 Final Validation

## Implementation

v1278 Security and Privacy Hardening strengthens existing authority-bearing seams rather than creating a parallel security product. It adds canonical path validation, link/junction/reparse awareness, source/runtime separation, content-minimized provider and project evidence, malicious archive validation, secret-scan non-follow behavior, package-read containment, and immediate pre-mutation path revalidation for governed self-update and controlled application.

The hardened package reader no longer depends on callers having already sanitized a path. The secret scanner does not dereference link/reparse targets. Dependency requirement includes reject unsafe/link-mediated traversal. Governed update and controlled application narrow time-of-check/time-of-use exposure by rechecking affected paths immediately before writes/restores/deletes while retaining the original exact authorization contracts.

## Focused and retained evidence

- v1278.0-v1278.2: **146/146**.
- v1278.3-v1278.5: **134/134**.
- v1278.6-v1278.8: **70/70**.
- v1278.9: **27/27**.
- v1277.9: **23/23**.
- v1276.9: **15/15**.
- v1275.9: **13/13**.
- v1274.9: **12/12**.
- v1273.9: **11/11**.
- v1272.9: **11/11**.
- v1271.9: **9/9**.
- v1270.9: **8/8**.
- v1269.9: **8/8**.
- v1269.6-v1269.8: **14/14**.
- v1256.9: **40/40**.
- v1255.9: **31/31**.
- v1255.0-v1255.2: **44/44**.
- v1255.3-v1255.5: **43/43**.
- v1255.6-v1255.8: **50/50**.
- v1247.9: **59/59**.
- v1196.9: **248/248**.
- checkpoint registry consolidation: **118/118**.

## Authority and privacy

Security inspection, path validation, archive inspection, secret metadata classification, and preflight evidence grant no execution authority. Generic conversational language remains non-authorizing. Provider material is represented by bounded digests/status only. Source-only package rules still exclude runtime data, conversations, memories, prompts, responses, provider payloads, secrets, logs, caches, environments, credentials, and private state.

## Remaining limitations

Python path revalidation narrows but cannot eliminate a hostile same-machine TOCTOU race between the last validation and an OS-level filesystem operation. Full descriptor/handle-based no-follow mutation semantics are platform-specific and remain a candidate for later hardening if native evidence warrants it. Windows junction/reparse behavior, NTFS sharing violations, Defender/indexer contention, ADS/device names, casefold/trailing-dot behavior, UNC/`\\?\` paths, and forceful ancestor swaps require Desktop Codex validation.

v1279 Operator Experience has not been started.
