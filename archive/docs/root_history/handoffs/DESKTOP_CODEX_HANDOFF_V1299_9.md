# Desktop Codex Handoff — v1299.9

Review the v1299 final supervised-autonomy rehearsal on native Windows/Desktop, focusing on process lifetime, restart timing, NTFS locks/reparse points, long paths, multi-process/UI behavior, and post-update/recovery timing. Confirm that the three evidence-integrity repairs reject altered canary observations, recovery triggers, and repeated-maintenance events without breaking valid fail-closed behavior.

The portable checkpoint must remain source-only and non-authorizing. v1269 exact one-time update authorization remains separately required and unconsumed by the rehearsal. General rollback remains separately governed. Native validation must not be inferred from Linux/provider-free evidence.
