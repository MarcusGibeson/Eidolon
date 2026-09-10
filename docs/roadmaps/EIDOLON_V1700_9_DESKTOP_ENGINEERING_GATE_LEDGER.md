# Eidolon v1700.9 Desktop Engineering Gate Ledger

This is the operator-invoked Windows engineering gate for the cumulative v1699.9 Era 2 Mobile Browser candidate. It records content-free evidence only. It grants no installation, promotion, certification, model-management, secret, destructive-operation, source-mutation, or independent authority.

## Input identity

- Input archive: `Eidolon_v1699_9_era2_mobile_browser_campaign_candidate_source_only.zip`
- Verified input ZIP SHA-256: `f409e8f47391dbaee912068362bbf65eb5a94d644c61c9e8817a449fa3f87f44`
- Expected source-manifest SHA-256 supplied at handoff: `bcd2985337e2cdfb3f26bdd672b1e052f88a4d368962b353ebb2ac439949780c`
- Candidate canonical manifest result: `9b70003d498bcf9b7c424c93a71c5431ea1c20aaecbf862200012b98f4bf7304` across 5,241 source-only files
- Candidate alternate source-only manifest result: `9c1dc338bdd0c1d54c15a0a391303af5d75fd3ac3889c7323163ed77ffb3b751`
- Finding: the supplied source-manifest hash matched neither embedded candidate algorithm. The exact ZIP hash, single-root layout, package privacy, and cumulative changed-file manifest remained independently verifiable. The final checkpoint therefore publishes newly computed hashes rather than repeating the stale supplied value.

## Cumulative review

- The v1600.9-to-v1699.9 ledger contains 13 added, 10 modified, and 0 deleted source-only paths.
- Every recorded candidate digest matched the extracted source and every baseline digest matched the operator-installed v1600.9 source.
- The cumulative changed-file manifest digest is `d9dec4e93ab5586815ecf56dff962674a3f362442cecb348b2f2c30176028558`.
- The checkpoint registry repair is retained: v1600.9 and v1699.9 each have one explicit canonical suite even though companion suites exist. v1700.9 also has one explicit canonical gate suite.

## Windows and native evidence

- The configured provider remained Ollama 0.32.15 with the operator's existing generation and embedding models. No model was installed, deleted, pulled, or switched.
- Readiness completed in 2.06 seconds. Native generation completed in 7.59 seconds, streaming in 0.17 seconds, and a 768-dimension embedding in 2.89 seconds; total smoke time was 12.71 seconds.
- Available Python, Node.js, PowerShell, Java, .NET, and PHP boundaries are exercised by the v1700.9 gate suite in disposable files. Missing Rust and Go installations are recorded as unavailable, not as failures or fabricated passes.
- A cloned external private runtime restored 383 memories and 70 conversation sessions. Doctor reported 92% and READY_WITH_WARNINGS with no blocker; the warnings were existing work-state observations rather than release-integrity failures.
- Fresh first-use bootstrap fell from 59.02 seconds to 0.28 seconds after removing private-runtime byte inventory from the startup path.
- Fresh browser restoration completed in 1.75 seconds with no console errors, no horizontal overflow, and a visible enabled composer at 100% zoom.

## Upgrade and rollback evidence

- A normal disposable v1600.9-to-candidate upgrade, verification, and rollback completed in 298.14 seconds.
- An interrupted upgrade after 97 copied files recovered and rolled back in 237.01 seconds.
- Baseline source, candidate source, and the operator's live installation remained unchanged.
- Upgrade source manifests and copies now exclude private runtime paths before hashing or copying, avoiding both privacy exposure and runtime-size-dependent work.

## Repaired integration defects

1. Native provider smoke nested a readiness receipt generated from bounded temporary timeout settings, causing its configuration digest to disagree with the configured identity. Readiness now separates operational settings from receipt identity, and certification tests bind both digests.
2. Portable upgrade simulation hashed and copied private runtime files before later excluding them. Source-only path selection now occurs before hashing and copying, with a private-runtime regression fixture.
3. First-use startup inventoried every byte of a large external runtime merely to present migration guidance. The ordinary bootstrap now performs a top-level presence check and defers full inventory to the explicit migration surface.
4. Dashboard response optimization replaced the first-use shell CSS with the unrelated full-dashboard stylesheet. Long histories expanded the page and pushed the composer off-screen. The optimizer now preserves the first-use layout contract, with source and rendered-browser regression evidence.
5. Release packaging treated the independent settings schema version as though it had to equal every product release. Packaging now validates the schema version against its own `last_updated_for` marker while product version remains governed by release authority.

## Verification boundary

- All 669 cumulative Browser checks reproduced on Windows before repair.
- A fresh compile covered 4,150 Python cache targets without source writes.
- The quick release verifier passed before repair and is rerun after checkpoint construction.
- Focused repaired suites, the v1700.9 native gate, release metadata, checkpoint registry, full release verification, package privacy, and final source immutability are required before packaging.
- Installation and promotion remain explicit future operator decisions.

## Next bounded unit

Era 3 begins at **v1701.0 - Requirements and Problem Framing foundations**. It should make problem statements, attributable requirements, constraints, uncertainty, acceptance criteria, and operator intent explicit before solution design or implementation begins.
