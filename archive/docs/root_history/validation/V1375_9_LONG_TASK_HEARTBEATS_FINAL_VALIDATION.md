# Eidolon v1375.9 Long-Task Heartbeats Final Validation

This checkpoint extends **Phase 8: Durable Multi-Step Campaigns** with durable long-task progress and control evidence.

- Heartbeats bind exact campaign/task lineage, monotonic sequence, bounded progress units, state, and observation time beneath an explicit external runtime root.
- Non-material heartbeat updates inside the configured interval are suppressed to avoid operator/runtime flooding; material progress or state changes persist immediately.
- Silence detection distinguishes a genuinely quiet running task from terminal states.
- Cancellation requests require explicit cancellation authority and persist only a content-minimized cancellation signal; the heartbeat layer does not stop a process itself.
- Timeout extensions are bounded recommendations derived from active progress and extension caps; no session/tool timeout budget is modified automatically.
- Tampered, regressive, malformed, or conflicting heartbeat records fail closed.
- Ordinary-chat inspection is read-only and import-lazy.

Focused verification: foundations 5/5; integration 6/6; reliability/adversarial 8/8; checkpoint 5/5. Retained release metadata passes 94/94 and checkpoint registry passes 118/118. A full five-arc segmented verifier is required before final packaging. No heartbeat or control record grants process-stop, timeout-budget mutation, project/source mutation, release, or independent authority.

## Five-arc broad verification

The canonical ten-stage segmented verifier completed against a frozen external snapshot with **10/10 stages passed, 0 failures, retained-checkpoints 16/16, source unchanged, runtime cleanup clean, exit 0**. Reported elapsed time was approximately **445.8 seconds**. Native Windows-only execution remains external evidence and is not claimed by this Linux host.
