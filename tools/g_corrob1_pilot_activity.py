from __future__ import annotations

"""Content-minimized Activity projection for the live mechanical pilot."""

import logging
from pathlib import Path
import sys
from typing import Any


CONTRACT_VERSION = "g-corrob1.mechanical-pilot.activity.1"
STAGES = ("pilot_preparing", "assessment_collection", "structural_validation",
          "paired_comparison", "mechanical_verification", "finalization")
ALLOWED_METRICS = frozenset({
    "scheduled_calls", "provider_contacts", "calls_completed", "A_completed", "B_completed",
    "validation_completed", "structural_failures", "pairs_completed", "comparisons_completed",
})


class NullPilotActivity:
    def emit(self, event: str, **kwargs: Any) -> None:
        return None


class PilotActivity:
    def __init__(self, run_id: str, *, root: str | Path) -> None:
        source = Path(__file__).resolve().parents[1] / "conscious_agent"
        if str(source) not in sys.path:
            sys.path.insert(0, str(source))
        from activity import Activity

        self.activity = Activity(
            run_id,
            "semantic_corroboration_mechanical_pilot",
            "G-CORROB1 live mechanical pilot",
            "Two-call blinded mechanics only",
            root=root,
            stages=STAGES,
            identities={
                "candidate_id": "G-CORROB1-pilot-capable-r3",
                "run_id": run_id,
                "record_namespace": "g_corrob1_mechanical_pilot",
            },
            governance={
                "read_only_observability": True,
                "belief_effects": "none",
                "pilot_only": True,
                "semantic_evaluation_permitted": False,
                "full_experiment_authority": False,
            },
        )

    def emit(self, event: str, **kwargs: Any) -> None:
        try:
            metrics = dict(kwargs.pop("metrics", {}) or {})
            if set(metrics) - ALLOWED_METRICS:
                raise ValueError("pilot_activity_metric_not_allowed")
            forbidden = {"breakdown", "result", "reason", "identities", "governance"} & set(kwargs)
            if forbidden:
                raise ValueError("pilot_activity_content_field_not_allowed")
            self.activity.update(str(event)[:100], metrics=metrics or None, **kwargs)
        except Exception:
            logging.getLogger(__name__).warning("G-CORROB1 pilot Activity projection unavailable: %s", event)


__all__ = ["CONTRACT_VERSION", "STAGES", "ALLOWED_METRICS", "NullPilotActivity", "PilotActivity"]
