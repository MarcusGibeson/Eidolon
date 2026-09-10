# v1255.3-v1255.5 Focused Validation

Bundle B turns a prepared v1255 application packet into a one-time supervised transaction while preserving a separately governed rollback boundary.

## Implemented

- Exact digest-bound phrase required to consume application authority once.
- Candidate workspace integrity rechecked before authorization consumption and private backup capture.
- Transactional create/modify/delete preflight followed by affected-path private backup capture immediately before the first write.
- Bounded live Python/Node verification without bytecode/cache debris in the selected project.
- Automatic affected-scope restore if post-apply verification fails.
- Successful applications produce a separately prepared rollback packet requiring another exact operator authorization.
- Rollback refuses to overwrite post-apply operator edits on affected paths.
- Replayed successful apply/rollback requests restore the sealed result instead of mutating again.
- Ordinary conversation routes explicit prepare/apply/rollback controls through the existing supervised-development campaign path.

## Deterministic focused evidence

`tools/v1255_3_5_controlled_application_integration_tests.py`: **43/43 passed**.

The suite uses the real provider-backed v1254 isolated execution path for its candidate lineage, then verifies controlled application, live tests, unrelated/private-file preservation, exact rollback, create/delete restoration, replay behavior, conversational controls, and source immutability.

Application authority does not imply installation, promotion, certification, release, unrestricted shell/dependency installation, permanent approval, or independent self-update authority.
