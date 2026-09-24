from __future__ import annotations

"""Conservative escalation triggers for G-ROUTE3 routing.

These are extra reasons to escalate an accepted output from a qualified tier. They are
never treated as evidence that an answer is correct, and they read no gold.

Changes from the G-ROUTE2 policy module, which is not modified:
- source_independence_insufficient is retired. Its condition, "an independent lineage
  was available for this claim", cannot be decided without knowing which sources are
  about which claim, which is a semantic judgment. Approximating it across the whole
  fixture fired on correct answers.
- grounding_weak tokenizes on every non-alphanumeric character and at every boundary
  between digits and letters, so a faithful restatement such as "11C for 40min." of
  "11 C for 40 min" is not mistaken for ungrounded text.
- grounding_weak's coding branch is removed: failed coding evidence is never accepted,
  so the branch could not fire on an accepted output and was dead code.

Defensive branches (round 3, stated rather than hidden): triggers are evaluated only on
operationally accepted outputs, and the operational validator already rejects unparseable
payloads, empty claim or statement lists, empty extraction values and failing coding output.
The corresponding branches below (the `value is None` returns, empty `claims` / `statements`
/ `steps`, extraction `[]`, coding `new == ""`) therefore cannot fire on an accepted output.
They are kept so the trigger functions are total over any payload. The live conditions are:
a settled research claim with no citation or lineage, a synthesis statement sharing no
content token with the observations it cites, a planning step with no evidence, and an
empty string value in an extraction field (each verified live by test). A synthesis
statement citing no observation is rejected operationally, so that branch is defensive too.
"""

import json
import re
from typing import Any, Mapping

CONTRACT_VERSION = "g-route3.triggers.v1"
GROUNDING_WEAK = "grounding_weak"
STRUCTURAL_ANOMALY = "structural_anomaly"
TRIGGERS = (GROUNDING_WEAK, STRUCTURAL_ANOMALY)
SETTLED_CLAIM_STATUS = frozenset({"supported", "contradicted"})
_TOKEN = re.compile(r"[a-z]+|[0-9]+")
_MIN_WORD = 4


def _parsed(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, Mapping):
        return dict(payload)
    try:
        value = json.loads(str(payload))
    except (TypeError, ValueError):
        return None
    return dict(value) if isinstance(value, dict) else None


def _content_tokens(text: Any) -> set[str]:
    """Alphanumeric tokens: every number, and every word of four or more letters."""
    return {token for token in _TOKEN.findall(str(text).casefold())
            if token.isdigit() or len(token) >= _MIN_WORD}


def grounding_weak(fixture: Mapping[str, Any], payload: Any) -> bool:
    profile = str(fixture.get("validator_profile") or "")
    if profile not in {"research.v1", "synthesis.v1", "planning.v1"}:
        return False
    value = _parsed(payload)
    if value is None:
        return True
    if profile == "research.v1":
        claims = value.get("claims")
        if not isinstance(claims, list) or not claims:
            return True
        for claim in claims:
            if not isinstance(claim, Mapping):
                return True
            if str(claim.get("status")) in SETTLED_CLAIM_STATUS:
                citations = [c for c in (claim.get("citations") or []) if isinstance(c, str)]
                lineages = [c for c in (claim.get("lineages") or []) if isinstance(c, str)]
                if not citations or not lineages:
                    return True
        return False
    if profile == "synthesis.v1":
        observations = {str(row["id"]): str(row["text"]) for row in fixture["input"]["observations"]}
        statements = value.get("statements")
        if not isinstance(statements, list) or not statements:
            return True
        for statement in statements:
            if not isinstance(statement, Mapping):
                return True
            cited = [item for item in (statement.get("observation_ids") or []) if isinstance(item, str)]
            if not cited:
                return True
            source = set()
            for item in cited:
                source |= _content_tokens(observations.get(item, ""))
            if source and not (_content_tokens(statement.get("text")) & source):
                return True
        return False
    steps = value.get("steps")
    if not isinstance(steps, list) or not steps:
        return True
    return any(not isinstance(step, Mapping)
               or not [item for item in (step.get("evidence_ids") or []) if isinstance(item, str)]
               for step in steps)


def structural_anomaly(fixture: Mapping[str, Any], payload: Any) -> bool:
    """Empty content in a field the profile requires to carry content."""
    profile = str(fixture.get("validator_profile") or "")
    if profile == "conversation.v1":
        return False
    value = _parsed(payload)
    if value is None:
        return True
    if profile == "extraction.v1":
        return any(item == "" or item == [] for item in value.values())
    if profile == "research.v1":
        return value.get("recommendation") == "" or value.get("claims") == []
    if profile == "synthesis.v1":
        return value.get("conclusion") == "" or value.get("statements") == []
    if profile == "planning.v1":
        return value.get("steps") == []
    if profile == "coding.v1":
        return value.get("new") == ""
    return False


def triggers_for(fixture: Mapping[str, Any], payload: Any) -> list[str]:
    fired = []
    if grounding_weak(fixture, payload):
        fired.append(GROUNDING_WEAK)
    if structural_anomaly(fixture, payload):
        fired.append(STRUCTURAL_ANOMALY)
    return fired


__all__ = ["CONTRACT_VERSION", "TRIGGERS", "GROUNDING_WEAK", "STRUCTURAL_ANOMALY", "grounding_weak",
           "structural_anomaly", "triggers_for"]
