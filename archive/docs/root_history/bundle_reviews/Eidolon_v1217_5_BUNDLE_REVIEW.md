# v1217.5 Bundle Review

## Scope

Conversational Repaired-Candidate Apply Execution.

## Result

- Added exact ordinary-chat authorization for one transactional apply.
- Sealed a private rollback manifest and one-use authorization receipt before the first project write.
- Applied only the exact changed repaired-candidate files and digest-verified the target state.
- Transaction failures restore the exact source workspace and return to operator review.

## Authority boundary

Apply authorization is limited to one exact project transaction. It grants no rollback execution, installation, promotion, release, model-management, or independent authority.

## Focused evidence

`tools/v1217_3_5_supervised_repaired_candidate_apply_execution_tests.py`: **54/54 passed**.
