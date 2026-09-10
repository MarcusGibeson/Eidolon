# v1276.0-v1276.9 Focused Validation

- v1276.0-.2 foundations: 35/35.
- v1276.3-.5 integration: 27/27.
- v1276.6-.8 reliability: 19/19.
- v1276.9 read-only checkpoint: 15/15.
- retained v1250.6 self-maintenance decomposition: 84/84.
- retained v1250.7 dashboard shell decomposition: 76/76.
- retained v1250.8 API catalog/HTTP runtime decomposition: 90/90.
- retained v1275.9: 13/13.
- retained v1274.9: 12/12.
- retained v1273.9: 11/11.
- retained v1272.9: 11/11.
- retained v1271.9: 9/9.
- retained v1270.9: 8/8.
- retained v1269.9: 8/8.
- retained v1256.9: 40/40.
- retained v1244.9: 125/125.
- release metadata consolidation: 94/94.
- checkpoint registry consolidation: 118/118.
- privacy/security checkpoint: 59/59; 0 confirmed/likely secrets; 10 intentional synthetic canaries.

The checkpoint itself is read-only and does not execute the reliability subprocess probes. Those probes remain in the retained v1276.6-.8 suite, preserving the checkpoint's no-command/no-test contract.
