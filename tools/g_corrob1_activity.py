from __future__ import annotations

"""Content-minimized G-CORROB1 projection into shared Activity v1."""

import logging
from pathlib import Path
import sys
from typing import Any


STAGES = ("preflight_validation", "assessment_collection", "structural_validation",
          "paired_comparison", "scoring", "finalization")
ALLOWED_METRICS = frozenset({
    "items_completed", "pairs_completed", "A_completed", "B_completed", "scheduled_calls",
    "provider_contacts", "returned_responses", "validation_completed", "structural_failures",
    "grounding_failures", "comparisons_completed", "scoring_units_completed",
    "extractions_completed", "extraction_failures",
})


class NullCorrobActivity:
    def emit(self, event: str, **kwargs: Any) -> None:
        return None


class CorrobActivity:
    def __init__(self, run_id: str, *, root: str | Path) -> None:
        source = Path(__file__).resolve().parents[1] / "conscious_agent"
        if str(source) not in sys.path:
            sys.path.insert(0, str(source))
        from activity import Activity

        self.activity = Activity(
            run_id, "semantic_corroboration_experiment", "Blind repeated semantic assessment",
            "G-CORROB1-R2", root=root, stages=STAGES,
            identities={"candidate_id": "G-CORROB1-candidate-r2", "run_id": run_id},
            governance={"read_only_observability": True, "belief_effects": "none",
                        "execution_authority": "external_explicit_authorization_required"},
        )

    def emit(self, event: str, **kwargs: Any) -> None:
        try:
            metrics = dict(kwargs.pop("metrics", {}) or {})
            if set(metrics) - ALLOWED_METRICS:
                raise ValueError("activity_metric_not_allowed")
            forbidden = {"breakdown", "result", "reason", "identities", "governance"} & set(kwargs)
            if forbidden:
                raise ValueError("activity_content_field_not_allowed")
            self.activity.update(str(event)[:100], metrics=metrics or None, **kwargs)
        except Exception:
            logging.getLogger(__name__).warning("G-CORROB1 Activity projection unavailable: %s", event)


__all__ = ["STAGES", "ALLOWED_METRICS", "NullCorrobActivity", "CorrobActivity"]
