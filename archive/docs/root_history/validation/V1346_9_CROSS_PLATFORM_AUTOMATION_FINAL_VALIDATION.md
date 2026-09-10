# Eidolon v1346.9 Cross-Platform Automation Final Validation

- Explicit Windows and POSIX targets; argument vectors remain authoritative and rendered shell strings are display-only.
- Windows path/quoting semantics reuse the v1345 Windows-first contract rather than being weakened by a generic POSIX abstraction.
- POSIX candidate scripts receive real `sh -n` syntax validation and focused real-process execution on this host.
- Environment overrides are bounded and known loader/interpreter injection variables are filtered.
- Candidate-only file/Git/process execution preserves selected-source immutability and cleans the disposable workspace.
- Windows native execution remains unvalidated on this Linux host; no release, install, network, or independent authority is granted.
