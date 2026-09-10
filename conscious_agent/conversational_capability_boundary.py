from __future__ import annotations

"""Distinguish tool-catalog requests from reflective capability conversation."""

import re

CONTRACT_VERSION = "v1500.9"

_EXPLICIT_CATALOG = re.compile(
    r"\b(?:which capabilities|what capabilities|what supervised actions|which supervised actions|"
    r"what (?:supervised )?(?:things|actions|commands|capabilities) (?:can|could) you (?:do|run|handle))\b",
    re.IGNORECASE,
)
_STANDALONE_WHAT_CAN_YOU_DO = re.compile(
    r"^\s*(?:please[, ]+)?what can you do(?: for me| through (?:this )?chat| in (?:this )?chat| as (?:a )?supervised assistant)?\s*[?.!]*\s*$",
    re.IGNORECASE,
)
_REFLECTIVE_CONTEXT = re.compile(
    r"\b(?:now that you|couldn['’]?t do before|could not do before|compared (?:with|to) before|"
    r"your (?:own )?progress|you(?:'ve| have) learned|grown|growth|improved|better at|"
    r"frustrates? you|your limitations?|feel about|proud of|struggle with|still can['’]?t|"
    r"still cannot|wish you could)\b",
    re.IGNORECASE,
)


def is_supervised_capability_catalog_request(text: str) -> bool:
    """Return true only for a request to inspect registered supervised tools."""
    value = " ".join(str(text or "").split())[:4096]
    if not value or _REFLECTIVE_CONTEXT.search(value):
        return False
    return bool(_EXPLICIT_CATALOG.search(value) or _STANDALONE_WHAT_CAN_YOU_DO.fullmatch(value))


def capability_boundary_receipt(text: str) -> dict[str, object]:
    value = " ".join(str(text or "").split())[:4096]
    return {
        "contract_version": CONTRACT_VERSION,
        "catalog_request": is_supervised_capability_catalog_request(value),
        "reflective_context": bool(_REFLECTIVE_CONTEXT.search(value)),
        "contains_message_content": False,
        "provider_contacted": False,
        "authority_granted": False,
    }


__all__ = [
    "CONTRACT_VERSION",
    "is_supervised_capability_catalog_request",
    "capability_boundary_receipt",
]
