# G-ROUTE1 Scientific Execution Authorization Handoff

G-ROUTE1 is repaired, deterministically verified, audited, and frozen for operator review. No scientific model call or benchmark launch occurred during the repair.

## Candidate

- status: `READY_FOR_EXPLICIT_SCIENTIFIC_EXECUTION_AUTHORIZATION`
- candidate: `G-ROUTE1-EXECUTION-R2`
- repair commit: `a1f314daead54fceac4bca12e703b001fccd2f08`
- execution-freeze content SHA-256: `feebf0e418e0cdab94463cdc0464c701e61a867deab72ee1cf93b26a33d7dfb1`
- execution-freeze literal SHA-256: `77138604fc0b63b6860b1b9c0aaa4b43b68cd7560e8a4f8dfffabfdc1d1673cf`
- schedule SHA-256: `75d7e4abafb61238e570b4428ca6b6a059086401c631ccee07d6348ef8e0b27d`
- model-binding SHA-256: `cd65b291237460413ccaf14d3dbdc16931960f1db3c8793ba0f50e17bd0f1099`
- threshold SHA-256: `8ee20613126d87d07b4facf8a44370b415fdb0801305f9067e14e177de212ec4`

The original R1 freeze remains preserved byte-for-byte as `EXECUTION_FREEZE_CANDIDATE_R1.json` with literal SHA-256 `836ee16db8a6f92e08570473c1e553a8ff564e785feb2c80b9ceb56750770029`.

## Repair evidence

The scientific runner now seals a digest-bound terminal receipt and terminal checkpoint only after score, manifest, and Activity completion agree. A successful 216-call provider-free run ends with 216 calls persisted, completed position 216, next position 217, and all terminal views `complete`. Terminal resume fails before provider invocation; duplicate identical finalization is idempotent; scorer or provider failure cannot appear complete.

Before any scientific authorization, independently verify the current freeze, confirm its authority flags remain false, review `TERMINAL_CHECKPOINT_REPAIR_AUDIT.md`, and confirm the protected corpus, gold, validators, scorer, thresholds, schedule, policies, and model bindings retain their prior digests. Authorization, if granted later, must be one-shot and bound to this exact R2 freeze. Production routing and belief effects remain disabled.
