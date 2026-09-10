# Bundle Review — v1231.3-v1231.5

## Scope

Ordinary-Chat Review and Exact Operator Decisions.

## Result

- Added exact ordinary-chat preparation, inspection, listing, accept, reject, defer, and request-changes controls.
- Kept wishes, hypotheticals, suggestions, quotations, malformed controls, stale digests, and conflicting decisions inert or explicitly blocked.
- Added sealed append-only review receipts with exact revision-digest binding and deterministic replay.
- Acceptance records operator review but does not replace the original plan, resume a paused session, or grant execution authority.
- Added content-free CLI and GET-only API projections with no v1231 mutation endpoint.
- Focused suite: **90/90 passed**.

## Boundaries

Accepted revisions still require separately prepared, separately reviewed, fresh future authority before any execution or resume action.
