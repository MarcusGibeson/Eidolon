# Eidolon v1331.9 Tool Capability Registry Checkpoint Validation

This checkpoint opens Phase 4: Tool Use and Isolated Execution from the finalized v1330.9 Deliberative-Planning Checkpoint.

## Completed behavior

- Defines content-minimized capability contracts for file read, file patch, search, Git, shell, browser, build, test, and service tools.
- Each capability declares an input schema, side-effect classes, authority class, and evidence-bound availability state.
- Availability is reported as available or unavailable only when a Boolean observation is accompanied by evidence digests; otherwise the state remains `declared_not_probed`.
- Registry construction and inspection are read-only: they perform no capability probe, invoke no registered tool, start no process, contact no service, and create no execution authority.
- Sealed project-evidence persistence and ordinary-chat inspection expose capability lineage without persisting private project or command content.
- A capability declaration, availability observation, registry record, plan, or chat projection never grants permission to execute the tool.

## Focused deterministic evidence

The v1331 focused suites complete successfully:

1. `v1331_0_2_tool_capability_registry_foundations_tests.py` — 5/5
2. `v1331_3_5_tool_capability_registry_integration_tests.py` — 4/4
3. `v1331_6_8_tool_capability_registry_reliability_tests.py` — 4/4
4. `v1331_9_tool_capability_registry_checkpoint_tests.py` — 5/5

Retained release-governance evidence remains green:

- v1250.3 release-metadata consolidation: 94/94
- v1250.4 checkpoint-registry consolidation: 118/118

## Authority and platform boundary

v1331 describes tool capabilities and side effects only. It does not widen any standing grant, execute a command, create a mutation, access a provider, or bypass protected-action policy. Native Windows execution remains external evidence and is not claimed by this Linux/container validation host.

## Lineage

Authoritative input lineage begins from the supplied immutable v1320.9 package with SHA-256 `C5FDF652632EA7879301C5E78058DE2D55969584B3F71960059E0E902C810004`, followed by the completed immutable v1321.9-v1330.9 checkpoints. v1331.9 is packaged only after focused verification, retained release-governance verification, privacy review, fresh-extraction parity, and deterministic rebuild.
