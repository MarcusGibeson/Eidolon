# Desktop Codex Handoff — v1224.9

Review the v1224.9 source-only candidate from a fresh Windows extraction.

Confirm that Eidolon derives one privacy-safe prioritization from the exact current v1223 queue without replacing queue, proposal, history, or resumption receipts.

Verify that:

- objective queue evidence remains distinguishable from heuristic ranking factors;
- low, normal, high, and critical operator priorities plus explicit pins are deterministic;
- dependencies order eligible work and cycles or missing dependencies fail closed;
- blocked, abandoned, closed, duplicate-conflict, and dependency-cyclic work cannot enter a schedule;
- accepted prioritization review is required before schedule preparation;
- exact ordinary-chat priority, pin, dependency, review, schedule, and schedule-review controls remain distinct from casual language;
- stale queue, prioritization, schedule, malformed record, tampered override, and conflicting review evidence fail closed;
- schedules are bounded to 20 planning slots and preserve queue-item and project-reference isolation;
- accepted schedules are planning evidence only and do not dispatch or execute work;
- no request, path, project name, source content, provider output, test output, or runtime location is exposed;
- no operation reuses approval, contacts a provider, runs commands/tests, continues work, repairs, applies, rolls back, installs, promotes, certifies, releases, manages models, changes project/source bytes, runs in the background, dispatches work, or grants authority.

Run the four focused v1224 suites, retained v1223 suites, checkpoint CLI and GET API, registry discovery, privacy inventory, source immutability checks, and quick/full release profiles where the environment permits. Treat unavailable dependencies and timed-out inherited gates as limitations rather than passes.

Next bounded unit: v1225.0-v1225.2 Supervised Work Dispatch and Execution-Session Preparation Foundations.
