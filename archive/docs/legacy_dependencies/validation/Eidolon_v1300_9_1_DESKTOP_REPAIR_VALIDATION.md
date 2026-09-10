# Eidolon v1300.9.1 Desktop Repair Validation

## Scope

This repair preserves the v1254-v1300 supervised self-development capability arc while correcting Desktop Windows verification and retained-checkpoint coherence defects found during review of the v1300.9 source-only candidate.

## Repairs

- Historical checkpoints derive retained and successor state from the current version instead of requiring development to stop at their original boundary.
- The quick profile is bounded; the prior broad inventory remains available through the segmented verifier.
- Segmented suite paths are short enough for nested Windows fixtures.
- Child and descendant processes run in a Windows kill-on-close job when available, with process-group and `taskkill` fallbacks.
- The ordinary per-suite timeout remains 240 seconds. Segmented verification uses a 5,000-action medium persistent-state profile; the explicit full 20,000-action certification profile remains available with a 600-second ceiling. The retained stage has an 1,800-second total budget.
- Dashboard response tests use UTF-8 source reads and a Windows-appropriate startup deadline.
- Warm conversation performance uses the existing 125 ms median and 500 ms p95 budget after a real warm-up sample. Mixed maintenance contention has a separate 250 ms median and 750 ms p95 budget.
- Active metadata and documentation identify v1300.9.1 while retaining historical checkpoint lineage.

## Boundaries

The repair does not contact a provider, mutate an operator project, install or delete models, modify the installed Eidolon instance, promote a release, or grant independent/self-update authority. The v1300 exact update and recovery demonstration remains fixture-bound and separately governed.

## Required Final Evidence

- Fresh Python compilation.
- v1300 focused foundations, integration, reliability, and checkpoint suites.
- v1254.9-v1300.9 retained checkpoint sequence.
- Segmented retained-checkpoint and dashboard-interface stages from clean snapshots.
- Bounded quick release verification.
- Windows dashboard startup and HTTP runtime/status probes with external runtime data.
- Source-only archive privacy scan and fresh-extract source parity.
