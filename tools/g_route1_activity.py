from __future__ import annotations

"""Content-minimized G-ROUTE1 projection into shared Activity v1."""

from pathlib import Path
import sys
from typing import Any


STAGES = ("preparing", "collection", "validation", "scoring", "finalization")
ALLOWED_METRICS = frozenset({
    "scheduled_calls", "calls_completed", "provider_contacts", "structural_failures",
    "active_elapsed_seconds", "checkpoint_position",
})
ALLOWED_IDENTITIES = frozenset({"current_model_tier", "current_task_class", "current_fixture_id"})


class NullRouteActivity:
    def emit(self, event: str, **kwargs: Any) -> None:
        return None


class RouteActivity:
    def __init__(self, run_id: str, *, root: str | Path, resume: bool = False) -> None:
        source = Path(__file__).resolve().parents[1] / "conscious_agent"
        if str(source) not in sys.path:
            sys.path.insert(0, str(source))
        from activity import Activity

        if resume:
            self.activity = Activity.reopen(run_id, root=root)
        else:
            self.activity = Activity(
                run_id, "adaptive_cognitive_routing_benchmark", "Three-tier model qualification",
                "G-ROUTE1", root=root, stages=STAGES,
                identities={"benchmark_id": "G-ROUTE1", "run_id": run_id},
                governance={
                    "operational_telemetry_only": True, "production_routing": False,
                    "execution_authority": "external_explicit_authorization_required",
                    "belief_effects": "none",
                },
            )

    def emit(self, event: str, **kwargs: Any) -> None:
        metrics = dict(kwargs.pop("metrics", {}) or {})
        identities = dict(kwargs.pop("identities", {}) or {})
        if set(metrics) - ALLOWED_METRICS:
            raise ValueError("route_activity_metric_not_allowed")
        if set(identities) - ALLOWED_IDENTITIES:
            raise ValueError("route_activity_identity_not_allowed")
        forbidden = {"breakdown", "result", "reason", "governance"} & set(kwargs)
        if forbidden:
            raise ValueError("route_activity_content_field_not_allowed")
        self.activity.update(str(event)[:100], metrics=metrics or None, identities=identities or None, **kwargs)


__all__ = ["STAGES", "ALLOWED_METRICS", "ALLOWED_IDENTITIES", "NullRouteActivity", "RouteActivity"]
