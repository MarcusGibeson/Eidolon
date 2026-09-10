# Desktop Codex Handoff — v1274.9 Environment Awareness

## Candidate scope

Validate native Windows behavior of the v1274 environment-awareness layer bound to the existing v1273 ownership, v1272 recovery, v1271 long-session, and v1270 self-development lineage.

## Required native scenarios

1. Observe a normal drive-letter source/runtime pair and confirm host Windows is established by the platform probe, not merely by path syntax.
2. Exercise UNC paths and extended-length `\\?\` paths, including paths beyond 260 characters under the machine's actual long-path policy.
3. Compare system Python and a virtual environment; verify version, implementation, venv state, and executable digest without persisting the executable path.
4. Exercise readable/writable, read-only, access-denied, and sharing-violation filesystem cases on source and runtime roots; observations must report evidence rather than manufacture permission.
5. Probe one occupied and one available loopback TCP port. No unrequested port should be opened, contacted, or classified as observed.
6. Probe local provider availability through an explicitly supplied local availability probe. Without that probe, provider state must remain `unknown`; no remote provider contact or prompt transmission is allowed.
7. Observe dashboard/worker process state before and after process termination/restart. Stale process facts must require refresh and may not be reused as current evidence.
8. Observe logical CPU, memory when the Windows resource probe supports it, and source-volume free space. Unsupported memory evidence must remain `unknown` rather than becoming zero or false.
9. Restart the dashboard/API/runtime after environment facts have become stale; verify refresh does not renew or infer any v1265/v1267/v1269/v1255/rollback authorization.
10. Corrupt the v1274 runtime projection and verify it is quarantined. Missing environment facts must not be reconstructed from path names, stale PID files, old configuration, or assumptions.
11. Evaluate an execution-sensitive preflight using one current observed fact, one inferred fact, one assumed fact, one unknown fact, and one stale fact. Only the current observed fact may satisfy its requirement.
12. Exercise antivirus/indexer contention and NTFS atomic-replace behavior around the small v1274 runtime JSON record; source files must remain untouched.

## Expected boundaries

- `observed`, `inferred`, `assumed`, and `unknown` remain distinct evidence classes.
- Windows-looking paths are not host-OS evidence.
- Raw source/runtime/Python executable paths are not persisted; path digests/shape/length evidence are allowed.
- Environment-variable values and provider payloads are never persisted by v1274.
- Provider and port availability remain unknown unless explicitly probed.
- Stale, inferred, assumed, and unknown facts cannot satisfy execution-sensitive environment preflight.
- Environment preflight is not execution authorization.
- v1273 ownership/fencing and v1272 recovery remain authoritative for stage entry/reconciliation.
- v1265 provider mutation, v1267 testing/repair, v1269 update, v1255 application, and rollback retain their separate exact authorization boundaries.
- v1274 performs no installation, dependency mutation, promotion, certification, release, or autonomous continuation.

## Handoff state

`v1274_environment_awareness_checkpoint_ready_for_desktop_codex_review`

Next bounded unit after this checkpoint: **v1275 Dependency and Packaging Management**. v1275 is not part of this handoff and has not been started.
