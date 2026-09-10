# Desktop Codex Handoff - Eidolon v1263.9

## Candidate under review

Milestone: **v1263.9 Priority Selection Checkpoint**

Baseline lineage: v1262.9 Development Backlog Generation.

## What to review

1. Run the four v1263 focused suites on native Windows.
2. Confirm a validated v1262 backlog is not mutated when priority is selected.
3. Confirm default factor provenance is marked inferred and explicit bounded context is distinguishable.
4. Confirm exact ties return no selected work item.
5. Confirm near-ties expose the score margin and low confidence.
6. Confirm dependency-blocked work cannot outrank/select ahead of its prerequisite.
7. Change source/evidence after selection and confirm the old decision fails freshness/lineage validation.
8. Race duplicate selection from separate processes/tabs and confirm deterministic convergence without duplicated durable work or proposal creation.
9. Exercise Windows long paths, case-insensitive aliases, and actual junction/reparse boundaries through the v1261/v1262 inputs.
10. Tamper with evaluation scores and recompute outer digests; semantic validation must still reject the artifact.

## Authority assertions

The candidate must not create a development proposal, schedule work, invoke providers, execute commands/tests, mutate the selected project, install dependencies, apply source, install/release Eidolon, or grant self-update/independent authority.

Application remains separately governed by v1255. Isolated coding execution remains separately governed by v1254. v1264 Alternative Planning and Simulation is not part of this candidate.

## Next bounded unit after review

**v1264 Alternative Planning and Simulation**.
