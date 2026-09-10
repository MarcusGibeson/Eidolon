from __future__ import annotations

"""Strict conversational entry boundary for one supervised development cycle."""

import re


CONTRACT_VERSION = "v1501.2"

_CONTINUE = re.compile(
    r"(?:continue|resume) (?:your|the|this|current) supervised (?:self-)?development(?: cycle| initiative)?[.!?]*$",
    re.IGNORECASE,
)


def is_supervised_development_continuation(message: str) -> bool:
    return _CONTINUE.fullmatch(str(message or "").strip()) is not None


__all__ = ["CONTRACT_VERSION", "is_supervised_development_continuation"]
