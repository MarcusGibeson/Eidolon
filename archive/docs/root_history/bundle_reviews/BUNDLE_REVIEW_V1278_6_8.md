# v1278.6-v1278.8 Bundle Review

Security and privacy reliability hardening is complete. The bundle adversarially exercises malicious archive metadata, link/reparse containment, secret-scan non-follow behavior, long paths, source/runtime overlap, update/application ancestor swaps, dependency include containment, provider-material redaction, and Windows-specific path-shape hazards.

The native Windows handoff retains NTFS junction/reparse behavior, sharing violations, Defender/indexer races, UNC and extended-length paths, ADS/device-name behavior, and forceful mutation-time parent swaps for Desktop Codex verification rather than claiming synthetic parity with Windows.

Focused deterministic result: **70/70**.
