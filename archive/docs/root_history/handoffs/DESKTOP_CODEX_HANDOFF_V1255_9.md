# Desktop Codex Handoff: Eidolon v1255.9

## Candidate

Milestone: **v1255.9 Controlled Application and Rollback Checkpoint**

Review this source-only candidate as the completion of v1255. Do not treat review as installation, promotion, certification, release, permanent approval, or authorization to start v1256.

## Primary Desktop review targets

1. Create a real NTFS junction/reparse substitution on an affected candidate path and confirm preparation/application fails closed without touching the outside target.
2. Exercise case-insensitive collisions such as `helper.py` versus `Helper.py` on Windows and confirm packet preparation is blocked.
3. Exercise long Windows paths within supported policy limits and confirm containment/digest behavior remains coherent.
4. Interrupt application after one of multiple affected writes, expire the lease, restart, and confirm recovery restores/replays only known baseline/candidate states with a single authority consumption.
5. Interrupt rollback after partial restoration and confirm the separately authorized rollback completes from the known mixed state.
6. Mutate an affected project file after application and confirm rollback refuses to overwrite the operator edit.
7. Mutate an unrelated project file before application and confirm it is preserved while the reviewed candidate still applies.
8. Corrupt the private backup and confirm rollback preparation fails closed.
9. Verify live Python/Node checks do not leave `__pycache__`, `.pyc`, test caches, provider payloads, or other runtime debris in the selected project.
10. Run duplicate application requests from multiple Windows processes/tabs and confirm one mutation owner, one authorization consumption, fail-closed active duplicates, and sealed late replay.

## Expected authority behavior

- v1254 isolated-execution approval is **not** application approval.
- Application requires the exact request/application digest phrase.
- Successful application does **not** authorize rollback automatically.
- Rollback requires its own exact request/rollback digest phrase.
- Installation, promotion, certification, release, permanent approval, dependency installation, unrestricted shell authority, and independent self-update remain denied.

## Expected next step

If Desktop review is satisfactory, the next development section is **v1256 Persistent Development Sessions**. Do not begin it as part of this review.
