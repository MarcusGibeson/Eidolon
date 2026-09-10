# v1256.3-v1256.5 Focused Validation

## Scope

Bundle B integrates persistent sessions into the ordinary conversational development pipeline and proves continuity through a real v1254 implementation/repair sequence and v1255 apply/rollback sequence without duplicate execution.

## Implemented integration

- Ordinary controls can show/status or resume a persistent session by session or development-request identity.
- Proposal approval attaches the persistent session to the same v1254 request rather than creating a second request model.
- Isolated execution, review, controlled-application preparation, apply, rollback preparation, and rollback refresh the same durable session.
- Resume is observational. It reconstructs state and surfaces an already-existing exact authorization phrase; it does not consume or mint authority.
- Append-only, content-minimized progress receipts use an identity digest so repeated identical resumes converge rather than produce duplicate progress history.
- Failed and repaired verification evidence survives restart.

## Deterministic evidence

`tools/v1256_3_5_persistent_development_session_integration_tests.py`: **42/42 passed**.

The fixture follows ordinary conversation -> proposal approval -> persistent session -> failed implementation attempt -> bounded repair -> fresh-process restart -> controlled application -> duplicate replay -> separately authorized rollback. Provider call count remains exactly **2**, including after restart/resume/apply/replay/rollback.
