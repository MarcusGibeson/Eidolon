# v1204.9 Checkpoint Review

The selected-project lifecycle now has immutable apply and rollback checkpoints. The apply checkpoint binds eight stages and records whether the project is in the generated or safely restored state. A completed rollback produces a thirteen-stage successor that references the exact apply checkpoint and proves restoration to the original affected-file state.

The checkpoint adds no authority. It cannot create apply or rollback authorization, cannot repair failures, cannot release or certify Eidolon, and cannot expose selected-project paths or rollback bytes publicly.
