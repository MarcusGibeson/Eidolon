# Eidolon v1600.9 Desktop Gate Ledger

## Scope

This operator-invoked Windows gate reviews the cumulative v1599.9 Mobile Browser candidate. It grants no standing installation, promotion, certification, provider, model-management, destructive-operation, source-mutation, or independent authority.

## Evidence

- Candidate ZIP SHA-256 matched `d137f2279fb2cc9ca0547fa18ca633967b53dc1900f50d6f7a5449367b197b0d`.
- The archive had one `Eidolon/` root and no packaged runtime data, `projects.json`, caches, or bytecode.
- The cumulative changed-file manifest matched every candidate and v1501.3 baseline hash.
- Eleven Era 1 focused suites passed 297 checks; retained integration suites passed 413 checks.
- Fresh-source compilation passed for 4,125 Python files without source mutation.
- Quick release verification completed under its time budget; its pre-gate blocked state reflected required operator review, not a functional failure.
- The configured Ollama provider passed readiness, generation, streaming, and embedding smoke checks without provider or model switching.
- Private runtime compatibility was exercised from a disposable clone rather than the operator's live data.
- The first real gate defect was stale operator documentation. The repair restores dashboard, setup, verification, and current-history contracts.
- The v1450.9 Desktop fixture still read `data/settings.json` from source and coupled the settings schema to the product version. It now reads the external runtime boundary and uses disposable current-version package metadata.
- The multi-tab fixture scaled with the operator's complete private runtime and hashed the entire source tree twice. It now owns one disposable runtime subdirectory and hashes only the modules it exercises; whole-tree immutability remains the release verifier's responsibility. Cold and warm standalone runs both passed in approximately 13 seconds against the 60-second budget.
- A hidden Windows race run created one campaign across six processes and one active item across four concurrent selectors, with zero duplicates and successful restart recovery.

## Remaining Human Gate

Automated and native evidence cannot replace ordinary daily use. Continue conversational and supervised-development trials after restart, recording only concrete defects. Installation and any later promotion remain operator decisions.
