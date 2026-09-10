# Windows / Desktop Codex Handoff: v1200.6 Development Candidate

1. Verify the candidate ZIP SHA-256 supplied with the handoff.
2. Extract beneath exactly one `Eidolon/` root in a disposable Windows directory.
3. Confirm `data/`, conversations, memories, prompts, provider payloads, credentials, runtime receipts, projects.json, private paths, and nested archives are absent.
4. Run `python tools/v1200_4_6_grounded_project_planning_tests.py` with `PYTHONDONTWRITEBYTECODE=1` and `PYTHONPATH=conscious_agent`.
5. Run the bounded quick release profile.
6. In ordinary chat, create a small website proposal, approve the exact proposal id and revision, and verify the response reports a grounded plan without provider generation or created implementation files.
7. Select a disposable small HTML/JavaScript or Python project and verify planning reads only allowlisted files, leaves the project byte-identical, and exposes only digest-based public evidence.
8. Verify stale revisions, missing approval, missing paths, symlinks, oversized files, excessive file counts, and unsupported project types stop safely.
9. Confirm the calculator Developer Alpha remains functional.

Do not install, promote, certify, or replace the v1200.0 operator baseline. This artifact is a development candidate only.
