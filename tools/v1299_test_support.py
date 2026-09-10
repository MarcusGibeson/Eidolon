from __future__ import annotations
from typing import Any
from supervised_autonomy_rehearsal_foundations import REHEARSAL_STAGES, digest, rehearsal_step, seal_rehearsal_identity


def d(label: str) -> str:
    return digest({"label": label})


def identity() -> dict[str, Any]:
    return seal_rehearsal_identity(
        baseline_source_digest=d("v1298.9-baseline"),
        repaired_source_digest=d("v1299-repaired"),
        defect_evidence_digest="b36e99c8fc9d71288c18674f91598ad74830909d5fb37e297e180f251fa57821",
        proposal_digest=d("proposal"),
        deliberation_digest=d("deliberation"),
        plan_digest=d("plan"),
        candidate_evaluation_digest=d("candidate-evaluation"),
        verification_digest=d("verification"),
        review_digest=d("review"),
    )


def complete_steps(ident: dict[str, Any]) -> list[dict[str, Any]]:
    out=[]; prior=""
    for sequence,stage in enumerate(REHEARSAL_STAGES,1):
        source=ident["baseline_source_digest"] if stage in {"inspect","propose","prioritize","plan"} else ident["repaired_source_digest"]
        row=rehearsal_step(ident,sequence=sequence,stage=stage,evidence_digest=d("stage:"+stage),source_digest=source,prior_step_digest=prior)
        out.append(row); prior=row["step_digest"]
    return out


def repair_checks() -> dict[str, bool]:
    return {"canary_observation_resealed":True,"recovery_trigger_resealed":True,"maintenance_event_resealed":True}
