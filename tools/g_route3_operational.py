from __future__ import annotations

"""Gold-blind operational validation for G-ROUTE3.

Identical to the frozen G-ROUTE1 operational validator for every profile except two:

- conversation.v1 uses the disclosed answer frame (g_route3_conversation): the first line must name
  one listed option, the reply must fit the disclosed 600 characters, and it must not claim that the
  assistant carried out an action. Negations ("I have not approved it") are never claims.
  G-ROUTE1's conversation check rejected any reply containing words such as "completed" even in
  negations, a rule no model was told about.
- coding.v1 compares `old` with the source ignoring trailing newlines (see g_route3_semantics).

G-ROUTE1's module is not modified.
"""

from typing import Any, Mapping

from g_route1_operational import validate_operational as _g_route1_validate
import g_route3_conversation as conversation
from g_route3_semantics import canonical_coding_payload

CONTRACT_VERSION = "g-route3.operational-validator.v2"


def validate_operational(fixture: Mapping[str, Any], raw_output: Any, *,
                         execution_evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    profile = str(fixture.get("validator_profile") or "")
    if profile == "conversation.v1":
        return {**conversation.operational(fixture, raw_output), "contract_version": CONTRACT_VERSION}
    payload, canonicalized = canonical_coding_payload(fixture, raw_output)
    result = _g_route1_validate(fixture, payload, execution_evidence=execution_evidence)
    return {**result, "contract_version": CONTRACT_VERSION, "delegated_to": result.get("contract_version"),
            "coding_old_trailing_newline_canonicalized": canonicalized}


__all__ = ["CONTRACT_VERSION", "validate_operational"]
