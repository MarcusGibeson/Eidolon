# v1201.3-v1201.5 Isolated Workspace Browser Preview Review

## Implemented
- Opaque, revision-bound browser preview URLs backed only by the verified external implementation workspace.
- Strict path normalization, traversal rejection, symlink rejection, MIME allowlisting, and a 1 MiB per-asset preview budget.
- Browser response protections: no-store caching, `nosniff`, no-referrer, and a restrictive content-security policy.
- Content-free preview evidence for HTML structure, title, viewport metadata, local asset count, missing asset digests, and entrypoint digest.
- Idempotent preview resume and tamper detection.
- POST-only preview creation and a dashboard action that opens the isolated preview in a separate browser tab.

## Authority boundary
No selected-project application, source mutation, shell command, browser automation, JavaScript execution, test execution, provider contact, model management, release promotion, or independent authority is introduced.

## Deferred
v1201.6-v1201.8 should add bounded browser and JavaScript validation adapters against the isolated workspace. Preview evidence in this bundle is structural and delivery-oriented, not a claim that application behavior has passed automated browser tests.
