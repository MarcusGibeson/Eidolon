# v1215.9 Final Validation

## Focused v1215 evidence

- v1215.0-v1215.2: **40/40 passed**.
- v1215.3-v1215.5: **51/51 passed**.
- v1215.6-v1215.8: **31/31 passed**.
- v1215.9: **66/66 passed**.
- Complete v1215 chain: **188/188 passed**.

## Retained evidence

- Retained v1214: **321/321 passed**.
- Retained v1213: **293/293 passed**.
- Retained v1212: **136/136 passed**.
- Retained v1211: **177/177 passed**.
- Retained v1210: **110/110 passed**.
- Retained v1209: **362/362 passed**.
- Small-project reliability: **77/77 passed**.
- Node/JavaScript checkpoint: **80/80 passed**.
- Python checkpoint: **70/70 passed**.
- Disposable compilation: passed with cache cleanup and no source mutation.

## Environment limitations

- The browser checkpoint cannot launch because this environment has no discoverable Playwright/Chromium runtime.
- The ordinary-chat runtime, natural conversation/command-distinction runtime, and the 46-check v1200 benchmark cannot import because the declared `requests` dependency is unavailable.
- Quick aggregate profile: **101.607 seconds**, within budget, blocked rather than passed.
- Full aggregate profile: **374.896 seconds**, within budget, blocked rather than passed.
- Both profiles preserved the identical 2,628-file source snapshot with zero source writes or deletes and did not time out.
- Aggregate blocks are inherited environment and retained smoke/integrity debt. They are not represented as v1215 assertion failures or global-profile passes.

## Source and package evidence

- Exact delta from immutable v1214.9: **13 new files, 8 modified files, 0 removed files**.
- Browser, Node, Python, unified-adapter, v1210 loop, v1212 continuation, and small-project coordinator implementations remain byte-identical to v1214.9.
- Root inventory before packaging: **2,628 source files**, zero symlinks, zero cache/bytecode entries, and zero forbidden runtime directories.
- Workspace-path scan: zero current-workspace or extraction-path findings.
- Credential scan: zero credential material. Retained private-key marker strings in `self_maintenance.py` are deliberate rejection fixtures and are byte-identical to v1214.9.
- Preliminary source-only archive: **2,628 unique files**, exactly one `Eidolon/` root, zero duplicates, directory entries, symlinks, unsafe paths, or forbidden runtime/cache entries.
- Preliminary fresh extraction: exact byte parity with the intended source tree.
- Preliminary fresh-extract v1215 replay: **188/188 passed**.
- Preliminary fresh-extract disposable compilation: passed with cache cleanup and zero extracted-tree mutations.
- Final immutable archive: **2,628 unique files**, exactly one `Eidolon/` root, zero duplicates, directory entries, symlinks, unsafe paths, forbidden entries, or private-content findings.
- Final fresh extraction: exact byte parity with the intended source tree.
- Final fresh-extract v1215 replay: **188/188 passed**.
- Final fresh-extract disposable compilation: passed with cache cleanup and zero extracted-tree mutations.
- Independent deterministic rebuild: byte-identical to the final archive.

## Authority statement

The candidate is source-only, uninstalled, unpromoted, uncertified, and release-unauthorized. Repair execution is limited to one exact operator-authorized isolated attempt. Every repaired candidate requires operator review; selected-project apply, Eidolon-source mutation, installation, promotion, release, model management, and independent authority remain unavailable.
