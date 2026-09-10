# v1278.0-v1278.9 Focused Validation

## v1278 results

- v1278.0-v1278.2 foundations: **146/146**.
- v1278.3-v1278.5 integration: **134/134**.
- v1278.6-v1278.8 reliability: **70/70**.
- v1278.9 read-only checkpoint: **27/27**.

## Retained affected evidence

- v1277.9 Development Observability: **23/23**.
- v1276.9 Architecture Boundary Extraction: **15/15**.
- v1275.9 Dependency and Packaging Management: **13/13**.
- v1274.9 Environment Awareness: **12/12**.
- v1273.9 Ownership and Concurrency: **11/11**.
- v1272.9 Restart and Crash Recovery: **11/11**.
- v1271.9 Long-Running Work Sessions: **9/9**.
- v1270.9 Self-Development Alpha: **8/8**.
- v1269.9 Governed Self-Update: **8/8**.
- v1269.6-v1269.8 governed-update reliability: **14/14**.
- v1256.9 Persistent Development Sessions: **40/40**.
- v1255.9 Controlled Application and Rollback: **31/31**.
- v1255.0-v1255.2: **44/44**.
- v1255.3-v1255.5: **43/43**.
- v1255.6-v1255.8: **50/50**.
- v1247.9 Privacy, Security, and Secret-Management Audit: **59/59**.
- v1196.9 Adversarial Privacy, Authority, Replay, and Recovery: **248/248**.
- checkpoint registry consolidation: **118/118**.

## Findings

Two normalization-order defects were discovered in the new v1278 validators during adversarial testing and repaired without weakening the attack fixtures: `./` ambiguity is rejected before `PurePosixPath` normalization, and absolute ZIP-entry detection occurs before leading-slash canonicalization. Existing package/update/application behavior remains governed by its original exact-authorization boundaries.

Security evidence is content-minimized and grants no provider, command, test, retry, repair, source/project mutation, installation, application, update, rollback, release, permanent, or autonomous authority.
