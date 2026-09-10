# v1210.9 Final Validation

- Complete focused v1210 suites: **110/110 passed**.
- Retained v1209 suites: **362/362 passed**.
- Affected v1205.8 small-project reliability: **77/77 passed**.
- Affected v1207.9 Node checkpoint: **80/80 passed**.
- Affected v1208.9 Python checkpoint: **70/70 passed**.
- Affected v1206.9 browser checkpoint: expected pass assertion was not reached because Playwright/Chromium is unavailable; dependency/environment limitation, not a pass claim.
- Retained v1205.9 and v1206.2 ordinary-runtime suites: could not import because the declared `requests` dependency is unavailable; dependency limitation, not an assertion result.
- Disposable compilation: **passed**, zero source-tree mutation.
- v1200 46-check developer-alpha acceptance benchmark: could not start because `requests` is unavailable; no 46/46 result is claimed.
- Accumulated quick profile: completed in **103.166 seconds**, within budget, source unchanged, status **blocked**.
- Accumulated full profile: completed in **333.768 seconds**, within budget, source unchanged, status **blocked**.
- Both profiles executed all four v1210 stages and preserved the same 2,569-file source snapshot with zero source writes or deletes. Required retained checks did not all pass, so aggregate verification evidence is invalid and no profile pass is claimed.
- Source-only archive: **2,567 unique files**, exactly one `Eidolon/` root, zero missing/extra/modified archived bytes against the intended source inventory.
- Root and final-archive privacy: zero forbidden entries and zero private-content findings.
- Fresh-extract v1210 replay: **110/110 passed**.
- Fresh-extract disposable compilation: **passed**, zero extracted-tree mutation.

No pass is claimed for a layer until its final result is recorded.
