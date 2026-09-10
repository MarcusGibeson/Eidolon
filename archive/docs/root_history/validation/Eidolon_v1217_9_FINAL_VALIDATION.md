# v1217.9 Final Validation

## Focused v1217 evidence

- v1217.0-v1217.2: **55/55 passed**.
- v1217.3-v1217.5: **54/54 passed**.
- v1217.6-v1217.8: **48/48 passed**.
- v1217.9: **69/69 passed**.
- Complete v1217 chain: **226/226 passed**.

## Retained evidence

- Retained v1216: **208/208 passed**.
- Retained v1215: **188/188 passed**.
- Retained v1214: **321/321 passed**.
- Retained v1213: **293/293 passed**.
- Retained v1212: **136/136 passed**.
- Retained v1211: **177/177 passed**.
- Retained v1210: **110/110 passed**.
- Retained v1209: **362/362 passed**.
- Small-project reliability: **77/77 passed**.
- Node/JavaScript checkpoint: **80/80 passed**.
- Python checkpoint: **70/70 passed**.
- Disposable compilation: passed with zero source mutation.

## Environment limitations

- The browser checkpoint cannot launch because this environment has no discoverable Playwright/Chromium runtime.
- The ordinary-chat runtime, natural conversation/command-distinction runtime, and the 46-check v1200 benchmark cannot import because the declared `requests` dependency is unavailable.
- Quick aggregate profile: **125.099 seconds**, within its 420-second budget, blocked rather than passed.
- Full aggregate profile: **329.419 seconds**, within its 1,800-second budget, blocked rather than passed.
- Both profiles ran all four v1217 stages, preserved the identical 2,654-file pre-validation source snapshot with zero source writes or deletes, and did not time out.
- Aggregate blocks are inherited environment and retained dashboard/smoke/integrity debt. They are not represented as v1217 assertion failures or global-profile passes.

## Source and package evidence

- Exact delta from immutable v1216.9: **13 new files, 8 modified files, 0 removed files**.
- Browser, Node, Python, unified-adapter, v1210 loop, v1212 continuation, v1215 supervised-repair executor, and small-project coordinator implementations remain byte-identical to v1216.9.
- Root inventory before packaging: **2,654 source files**, zero symlinks, zero cache/bytecode entries, and zero forbidden runtime directories.
- Workspace-path scan: zero current-workspace or extraction-path findings.
- Credential scan: zero new credential material. Retained private-key marker strings in `self_maintenance.py` are deliberate rejection fixtures and are byte-identical to v1216.9.
- Preliminary source-only archive: **2,654 unique files**, exactly one `Eidolon/` root, zero duplicates, directory entries, symlinks, unsafe paths, or forbidden runtime/cache entries.
- Preliminary fresh extraction: exact byte parity with the intended source tree.
- Preliminary fresh-extract v1217 replay: **226/226 passed**.
- Preliminary fresh-extract disposable compilation: passed with zero extracted-tree mutations.
- Final immutable archive: **2,654 unique files**, exactly one `Eidolon/` root, zero duplicates, directory entries, symlinks, unsafe paths, forbidden entries, or private-content findings.
- Final fresh extraction: exact byte parity with the intended source tree.
- Final fresh-extract v1217 replay: **226/226 passed**.
- Final fresh-extract disposable compilation: passed with zero extracted-tree mutations.
- Independent deterministic rebuild: byte-identical to the final archive.

## Authority statement

The candidate is source-only, uninstalled, unpromoted, uncertified, and release-unauthorized. One exact v1216 authorization may supervise one transactional apply of the sealed repaired candidate to the digest-bound selected project, with private rollback evidence and automatic restoration on apply failure. Every sealed outcome returns to operator review. Repeat apply, discretionary rollback, installation, promotion, release, model management, and independent authority remain unavailable.
