# Eidolon v1254.0-v1254.2 Bundle A Review

Bundle A establishes the bounded preparation layer for Isolated Coding Execution without beginning implementation execution or source application.

## v1254.0 - Bounded Coding Work Request Contract

- Added a durable coding-work-request contract for the user objective, selected project, requirements, acceptance criteria, constraints, prohibited actions, authority state, ambiguities, assumptions, expected artifacts, and verification expectations.
- Duplicate equivalent requests converge on the same deterministic request identity and restore the sealed runtime record instead of creating duplicate work.
- Dangerous authority remains explicitly denied. Read-only inspection, planning, and isolated snapshot materialization are represented separately as preparation capabilities rather than approvals.
- Public projections expose digests and counts rather than selected-project paths or request text.

## v1254.1 - Isolated Workspace and Project Inspection Foundations

- Added bounded project inspection with conservative source-file selection, project-type detection through the existing broader-project adapter layer, source manifests, content digests, and scan accounting.
- Excludes runtime/private/generated paths such as `data/`, conversations, memories, prompts, responses, provider payloads, logs, secrets, credentials, caches, virtual environments, dependency trees, and build output.
- Rejects traversal, symlinks, and Windows reparse points/junctions at containment boundaries.
- Added disposable workspace materialization under the existing development-campaign runtime store. Only files present in the sealed inspection inventory are copied, and every copied file is digest-verified before and after the copy.
- Records source and workspace manifests and refuses materialization when the selected source has become stale.
- Cancellation persistently closes the request and deterministically removes its disposable workspace.

## v1254.2 - Bounded Coding Planning and Reliability Foundations

- Added a sealed planning contract that maps requirements to candidate files, bounded implementation stages, verification expectations, acceptance criteria, assumptions, ambiguity/uncertainty, completion conditions, and blocker conditions.
- Planning cannot grant execution, command, test, provider, dependency-install, project-mutation, source-application, installation, release, permanent approval, or independent authority.
- Request, inspection, plan, and workspace records restore from disk across module reloads and remain idempotent.
- Added deterministic provider-free Bundle A tests for isolation, immutability, containment, private-data exclusion, idempotency, staleness, restart restoration, cancellation/cleanup, and denied authority.

## Scope Boundary

This bundle intentionally does **not** implement provider-driven code generation, unrestricted shell execution, test execution by the product, candidate application, installation, rollback, autonomous self-update, permanent approval, or ordinary-chat execution integration. Those remain later work.
