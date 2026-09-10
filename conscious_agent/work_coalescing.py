from __future__ import annotations

"""v1253.2 bounded per-turn work coalescing.

This helper only deduplicates repeated in-process reads/builds within one turn.
It has no persistent authority and never reuses a value across turns unless a
caller explicitly supplies the same TurnWorkCache instance.
"""

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Callable

CONTRACT_VERSION = "v1253.2"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass
class TurnWorkCache:
    values: dict[str, Any] = field(default_factory=dict)
    builds: int = 0
    hits: int = 0

    def get(self, key: str, builder: Callable[[], Any]) -> Any:
        token = str(key or "").strip()
        if not token:
            return builder()
        if token in self.values:
            self.hits += 1
            return deepcopy(self.values[token])
        value = builder()
        self.values[token] = deepcopy(value)
        self.builds += 1
        return deepcopy(value)

    def receipt(self) -> dict[str, Any]:
        row = {
            "contract_version": CONTRACT_VERSION,
            "unique_builds": self.builds,
            "coalesced_hits": self.hits,
            "keys": sorted(self.values),
            "turn_local_only": True,
            "provider_contacted": False,
            "authority_granted": False,
        }
        row["receipt_digest"] = _digest(row)
        return row


__all__ = ["CONTRACT_VERSION", "TurnWorkCache"]
