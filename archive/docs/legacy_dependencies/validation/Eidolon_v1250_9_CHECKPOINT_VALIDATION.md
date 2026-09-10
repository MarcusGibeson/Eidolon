# Eidolon v1250.9 Cleanup and Verification Hardening Checkpoint Validation

## Authoritative input

- Source-only baseline: `Eidolon_v1250_8_architecture_consolidation_oversized_module_decomposition_bundle_c_final_candidate_source_only.zip`
- Expected baseline SHA-256: `225DE55AB7697279440D830355323A444F453F0CC454266F932AAE29090011C3`
- Baseline treatment: immutable input extracted beneath exactly one `Eidolon/` root.

## Checkpoint scope

v1250.9 closes the v1250 cleanup arc. It adds no product capability and grants no autonomous authority. The checkpoint verifies:

1. one current release authority and generated metadata facade;
2. sixty uniquely resolved whole-version checkpoint records;
3. ten independently runnable verifier stages;
4. semantic conversation/command test selection;
5. atomic suite-level progress receipts;
6. independent runtime state and timeout budgets for every suite;
7. temporary-file output capture and residual process-group cleanup;
8. retained v1249 and v1250 compatibility;
9. source-only packaging and source immutability; and
10. readiness for the postponed Desktop Codex review.

## Defects repaired during checkpoint work

- The conversation stage previously invoked an unrelated browser-runtime checkpoint and could fail because of host Chromium policy. It now runs the natural-conversation command-distinction suite.
- Stage receipts previously exposed only stage-level progress. They now name the active suite, index, phase, and completed count before and after every suite.
- Successful test children could leave descendants holding inherited output pipes open. Output is now captured through external temporary files, and residual process groups are terminated after direct-child exit.
- Every suite now receives an isolated runtime root and an independent 180-second cap.

## Required external evidence

The final source-only archive must be accompanied by an external complete ten-stage segmented-verifier receipt. The receipt must show all requested stages completed, all stage receipts passed, source unchanged, runtime cleanup successful, and no authority grant. A passing receipt is evidence only; it does not install, promote, certify, release, contact providers, mutate projects, mutate source, or authorize independent continuation.
