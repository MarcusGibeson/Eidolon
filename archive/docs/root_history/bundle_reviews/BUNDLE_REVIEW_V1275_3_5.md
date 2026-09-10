# Bundle Review v1275.3-v1275.5

## Scope

Real v1274 environment integration and separately authorized clean-install verification.

## Implemented

- Dependency/package assessment bound to current v1274 environment and source-manifest lineage.
- Clean-install preflight satisfied only by current observed Python/source facts.
- Exact digest-bound authorization phrase; generic conversational approval is rejected.
- Default clean-install execution creates a disposable virtual environment and forces offline/no-index pip behavior.
- Installer stdout/stderr are represented only by digests in the receipt.
- Dependency-intent drift between authorization preparation and execution blocks the install before runner invocation.
- A real offline clean-install fixture executes successfully in a freshly created disposable environment.

## Authority boundary

The clean-install authorization is one bounded verification authorization. It grants no active-source dependency edit, standing install authority, provider authority, release authority, or reuse after intent drift.

## Focused evidence

`tools/v1275_3_5_dependency_packaging_integration_tests.py` — 26/26.
