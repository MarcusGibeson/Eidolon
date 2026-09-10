# Eidolon v2100.9 Desktop Attention and Initiative Gate Ledger

Status: Desktop-reviewed source-only checkpoint; unpromoted and not installed.

## Input identity

- Candidate ZIP SHA-256: `645b68cf64e1c7453f952f11d9fc84014499cf93f7ce4e8657253a5f53f2d9ea`
- Authoritative v2000.9 baseline SHA-256: `5c34311d77b479fce094a163af70afa2f1d39aa115df62f8ac19e77d953251da`
- Archive shape: one `Eidolon/` root; 5,306 entries; no packaged private runtime data, project registry, cache, bytecode, or Git metadata.
- The actual cumulative diff matched every declared path, change kind, and non-self-referential SHA-256: 14 added, 11 modified, 0 deleted.

## Windows and native evidence

- Focused Era 6 suites: 79/79 passed after repair.
- All 20 selected affected retained suites reproduced successfully, including release metadata and checkpoint-registry consolidation.
- Fresh compilation covered 4,183 cache targets without writing bytecode into source.
- Twelve concurrent Windows job writers created twelve jobs with no failures. Twelve processes sharing one wake ID converged on one primary tick, eleven idempotent replays, and two bounded prepared tickets.
- Quiet hours suppressed work; the first active-hour wake prepared one ticket; replay prepared none; a later wake recovered a missed due interval without duplication.
- Real host measurements above the configured background memory budget caused cooperative suspension without pausing or killing a process.
- Configured Ollama readiness, bounded generation, streaming, and 768-dimensional embeddings passed without model installation, deletion, or switching. Native conversation completed 12/12 scenarios at 99% average quality with one non-blocking continuity warning and zero duplicate requests, messages, actions, or persistent mutations.
- Quick and full release verification passed with source immutability.

## Desktop repairs

1. Resource assessment no longer converts absent, unknown, nonnumeric, negative, or nonfinite measurements into evidence of zero load. Insufficient evidence now suspends ordinary background preparation while foreground work remains outside this background-governance decision.
2. The operator-enabled scheduler is now invoked by Eidolon's existing 60-second cognitive service through a content-free native host bridge. Scheduling remains disabled by default, minute-slot replay is exactly once across processes, and only non-executing tickets can be prepared.

## Remaining limitations

- The scheduler prepares bounded tickets; a separate governed executor and capability-specific authority are still required before any ticket can perform external work.
- Proactive policy can queue reviewable candidates through the retained queue, but this gate does not grant unsolicited delivery authority.
- Optional native resource sampling uses `psutil` when available. If unavailable, the repaired policy suspends background preparation rather than guessing.
- Native conversation retained one non-blocking continuity-quality warning despite a 99% average score.
- This gate is not installation, promotion, certification, model management, destructive operation, or independent authority.

## Next bounded unit

`v2101.0 - Local System and Application Tool Contracts`
