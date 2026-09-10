from __future__ import annotations

"""v2539 bounded advisory signals for cognitive observability.

Interprets already-minimized observability metrics into operator-facing status
signals. Signals are descriptive only: they do not schedule cognition, modify
state, authorize actions, or claim medical/psychological meaning.
"""

import hashlib
import json
from typing import Any, Mapping

CONTRACT_VERSION = "v2539.0"
SEVERITIES = frozenset({"quiet", "normal", "notice", "elevated"})


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def build_cognitive_observability_signals(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping) or not snapshot.get("ok"):
        raise ValueError("valid_observability_snapshot_required")
    now = snapshot.get("now") if isinstance(snapshot.get("now"), Mapping) else {}
    recent_count = int(snapshot.get("recent_count") or 0)
    signals=[]

    pressure=float(now.get("pressure") or 0)
    fragmentation=float(now.get("fragmentation") or 0)
    uncertainty=float(now.get("uncertainty") or 0)
    conflicts=int(now.get("belief_conflicts") or 0)
    due=int(now.get("due_continuity_subjects") or 0)
    recovery=float(now.get("recovery_margin") or 0)

    if recent_count == 0 and pressure < 0.35 and conflicts == 0 and due == 0:
        signals.append({"code":"quiet_state","severity":"quiet","summary":"No recent durable cognitive activity needs operator attention."})
    if pressure >= 0.75 or fragmentation >= 0.75:
        signals.append({"code":"cognitive_load_elevated","severity":"elevated","summary":"Cognitive load or fragmentation is elevated in the current structural state."})
    elif pressure >= 0.5 or fragmentation >= 0.5:
        signals.append({"code":"cognitive_load_notice","severity":"notice","summary":"Cognitive load is above the ordinary low-pressure range."})
    if uncertainty >= 0.7:
        signals.append({"code":"uncertainty_elevated","severity":"notice","summary":"Current structural uncertainty is elevated."})
    if conflicts > 0:
        signals.append({"code":"belief_conflict_present","severity":"notice","summary":"The retained belief model reports unresolved conflict."})
    if due > 0:
        signals.append({"code":"continuity_due","severity":"notice","summary":"One or more unfinished continuity subjects are due for reconsideration."})
    if recovery <= 0.25 and (pressure >= 0.5 or fragmentation >= 0.5):
        signals.append({"code":"recovery_margin_low","severity":"elevated","summary":"Recovery margin is low while cognitive load remains elevated."})
    if not signals:
        signals.append({"code":"state_nominal","severity":"normal","summary":"No bounded observability signal currently stands out."})

    for row in signals:
        row["medical_interpretation"] = False
        row["action_authorized"] = False
        row["state_mutated"] = False
        row["signal_digest"] = _digest(row)

    overall = "elevated" if any(r["severity"]=="elevated" for r in signals) else "notice" if any(r["severity"]=="notice" for r in signals) else signals[0]["severity"]
    result={
        "ok":True,
        "contract_version":CONTRACT_VERSION,
        "overall":overall,
        "signals":signals[:8],
        "signal_count":len(signals[:8]),
        "authority_boundary":{
            "advisory_only":True,
            "can_schedule_cognition":False,
            "can_mutate_state":False,
            "can_authorize_action":False,
            "can_execute_action":False,
            "medical_or_psychological_diagnosis":False,
        },
    }
    result["result_digest"]=_digest({"overall":overall,"signals":signals[:8]})
    return result


__all__=["CONTRACT_VERSION","SEVERITIES","build_cognitive_observability_signals"]
