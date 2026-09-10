# v1278.0-v1278.2 Bundle Review

Security and Privacy Hardening foundations are complete. The bundle adds canonicalization-before-resolution rules for untrusted relative paths, symlink/junction/reparse detection, content-minimized project and provider-material inspection, runtime/source separation checks, exact-authorization boundary validation, archive-structure inspection, and explicit denial of inherited execution/update authority.

Adversarial fixtures cover traversal, absolute/drive/backslash/ADS/device-name ambiguity, case and normalization collisions, malicious ZIP link entries, compression/size limits, sensitive project names, private-field injection, and generic conversational approval.

Focused deterministic result: **146/146**.
