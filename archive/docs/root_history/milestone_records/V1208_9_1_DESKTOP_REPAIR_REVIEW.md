# v1208.9.1 Desktop Repair Review

## Repaired findings

- Python `pathlib.Path.write_text()` could escape the implementation workspace while tests reported success.
- Browser validation injected HTML rather than navigating the served project, so linked assets and modules were not exercised.
- Node 20.1 received an unsupported `--test-concurrency=1` flag.
- Windows directory-lock contention could surface as `PermissionError` or exhaust an eight-second timeout.
- Playwright and pytest requirements were not declared for the adapters and certification suites.
- The v1208.9 fixture depended on the Windows default text encoding.
- A wish and imperative joined by `and` in one sentence could lose the actionable clause.

## Boundary statement

The Python audit hook and Node preload guard block the reproduced file-write defects, network/process capabilities, and the tested bypasses. They are in-process language-runtime policies, not operating-system containers. The public receipts state this explicitly. Generated tests remain supervised evidence and do not receive repair, apply, release, or independent authority.

## Verification

Desktop repair verification passed the affected v1205.8, v1206.2, v1207.2, v1207.5, v1207.8, v1207.9, v1208.2, v1208.5, v1208.8, and v1208.9 suites. The v1205.8 Windows concurrency suite passed three consecutive runs. Compilation passed without writing bytecode into source, and the v1200 product-reality benchmark passed 46 of 46 checks.

The accumulated quick verifier did not complete inside a 30-minute wrapper; its non-smoke form also exceeded a separate 20-minute wrapper. Neither invocation returned a failing test result, but neither is represented as a pass. Its child processes were stopped after each wrapper timeout. Fresh-extract compilation, focused regression checks, source immutability, and archive privacy remain required for the delivered ZIP.
