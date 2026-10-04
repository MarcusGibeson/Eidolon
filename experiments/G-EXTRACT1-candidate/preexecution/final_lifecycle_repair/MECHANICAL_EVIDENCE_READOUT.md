# Mechanical Evidence Readout

Producer certification only; independent audit and execution-freeze activation are separate.

- Implementation commit: `29d6d7897cac83c66c02ca96711325381937b8db`.
- Pilot/evidence commit: `2a3bda951e7ae48802834712c38c9d6be1e27169`.
- 2,521 deterministic checks passed, including 322 LR checks and 176 I1-I6 regression checks.
- LR1: 137 checks; 17 malformed payloads and six envelope shapes; caught/restarted continuation transport calls zero.
- LR2: 143 checks; 23 unusable returns/exception cases and five valid outcome replays; START closed with governed FAILURE; later transport calls zero.
- LR3: 42 checks; all ten frozen precontact events give six A_BLOCKED cells; contacted failure cases never become A_BLOCKED.
- I1/I2/I3/I4/I5/I6: 15/38/22/10/8/83 checks respectively.
- Two complete synthetic pilots: 480 A plus 240 B observations each; all 1,447 files per tree byte-identical.
- Conditional B subsets: 64; E5 wire audits: 108; elapsed clarifications: 12.
- All 50 protected actual files verified. Corpus/gold/design/blueprint/thresholds unchanged.

## Schedule And Candidate Digests

- A: `3c48390307dd683e7ba2f736318d42f4d9fbda6527bbb9d64ee03b4bf97bb4dd`.
- Maximum B: `6361e990216be94ca3ad69b75b485adf70fc8a035b2e459e5d309063c8ea164b`.
- New unactivated candidate: `687a9a50d9bbbe480f3e74e103f5b75c621a46a9ffdcc8e80dab65f6b2915a35`.
- Old blocked candidates: `14fb601c3a58777942ccd0361c2a303b5bfcf10d4c05536a32d265c0babe537f`, `6e7295b3c79ee95930fee7231265e342905b7848d261ae716d1ef1546ca785ab`.

## Implementation SHA-256

- `tools/g_extract1_contract.py`: `078083bb966488d5c9da548f340cab8189d1d4a3b4bc19fac388b33598638c5c`.
- `tools/g_extract1_final_lifecycle_tests.py`: `d43471c0d3bb33d62720dbfd5ba9917e46b6aad2e0a431b0a9d1b0e7d73b88d2`.
- `tools/g_extract1_journal.py`: `d34755610eb71e787cf5325ea6f5719f530927720d8a0344746d1a50f11f5644`.
- `tools/g_extract1_lifecycle_tests.py`: `d63d1b78a5d66709787804a3cb8885abb6e6ba5225cf285dcf267f4f828e7165`.
- `tools/g_extract1_pilot.py`: `07e547daefc6fe74c9706a35f0723bb209b77cbd854f15b83b59519e8ba79c37`.
- `tools/g_extract1_runner.py`: `5bfcab71a8eef4986da971f542a73d1a8c759ed8ab5a396849964afce6ab2100`.
- `tools/g_extract1_scoring.py`: `e6d9b6171cdccf14da7a69a68b0e3558e632edde4e39d7920406d28c872be27f`.

## Preserved Untracked Authoring SHA-256

The pilot recorded these before certification and verified byte equality afterward. They remain unstaged.

- `AUTHORING_ATTEMPTS.json`: `b9860b6bd4f662c46935773463bf6caf78035a1c2aa01c0b6a55e5100b9aa8da`.
- `AUTHORING_CANDIDATES.json`: `f575c8d86ca82f2c5ea7727404d0c8bbb5a72f7b472abfd244471edb3180d068`.
- `AUTHORING_FEASIBILITY_REPORT.json`: `8767a025c1123541cc858873aff41b60ecc1f8b0186d72ccc738761a24771433`.
- `FINALIZATION_CONTAMINATION_DISAGREEMENT_REPORT.json`: `d9ff96223d36cd2c92d92361be028820d6955b82712f1ed2152178958c8765dc`.
- `FINALIZATION_FAILURE_REPORT.json`: `588b6141e3c25b561dff49d7b004ca508468ed39f4dbef8a8e16c54f69918730`.
- `FINALIZATION_HISTORICAL_REUSE_CONTRACT_STOP_REPORT.json`: `a011317172165d16569a78a975b861e8ccb7c374a68248da23f9c47498a8984d`.
- `FRESHNESS_CANONICALIZATION_DIAGNOSIS_REPORT.json`: `7395408dcf283821d19ed81f6986d64c47b4d31f9dd76d1c72481f7dff48a442`.

## Producer Report SHA-256

- `E5_HARNESS_WIRE_AUDIT.json`: `89bc4ac0fe7163ec5ccabde0e08574cea491e35567a06baddd33b93ae79bf3ed`.
- `EXECUTION_FREEZE_CANDIDATE.json`: `687a9a50d9bbbe480f3e74e103f5b75c621a46a9ffdcc8e80dab65f6b2915a35`.
- `FINAL_LIFECYCLE_REPAIR_REPORT.json`: `58db7848381ab480592cfe4c86675d3c6ac58d4c843e0e98b023906c97128a48`.
- `LIFECYCLE_REPAIR_REPORT.json`: `539ff36290bae73e918fb5e2d915547fb73b02e0e687d2b76817ed20e92dd1fe`.
- `MECHANICAL_PILOT_REPORT.json`: `3bc99456534dc3459f34ce7af4817663e875d5fe56b242f47e0437b65347afc6`.

## Governance

Provider/model and real A/B calls zero. No active freeze or actual phase authorization.
No science, corpus, gold or blueprint edits. G-ROUTE4 CLOSED FAILED unchanged.
Autonomy false; belief effects none. The independent audit status, not producer test count, controls closure.

