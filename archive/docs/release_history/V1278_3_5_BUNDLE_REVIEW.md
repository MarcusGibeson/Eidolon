# v1278.3-v1278.5 Bundle Review

Security hardening is integrated into the real source-package, secret-scan, governed self-update, controlled-application, dependency, provider-material, and runtime/source boundaries. Package byte reads now independently validate containment instead of trusting upstream manifest callers. Governed update/application paths revalidate the affected parent chain immediately before sensitive file operations, narrowing link/reparse swap windows without claiming descriptor-level race elimination.

The integration preserves exact authorization semantics and returns redacted/digest evidence rather than provider payloads, prompt/response content, secrets, or external-link target content.

Focused deterministic result: **134/134**.
