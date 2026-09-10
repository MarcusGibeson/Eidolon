from __future__ import annotations

"""Verification-evidence quality policy for current Eidolon releases.

Historical source-presence and documentation-marker checks remain useful for
compatibility and packaging drift, but they are structural evidence only.  A
current release may not claim a product behavior from those checks alone.
Behavioral claims require executable assertions over public/runtime behavior,
and security claims require negative/adversarial cases where feasible.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class EvidenceClass(str, Enum):
    BEHAVIORAL = "behavioral"
    ADVERSARIAL = "adversarial"
    INTEGRATION = "integration"
    STRUCTURAL = "structural"
    SOURCE_PRESENCE = "source_presence"
    SYNTHETIC_CONSISTENCY = "synthetic_consistency"
    HISTORICAL_COMPATIBILITY = "historical_compatibility"


CERTIFYING_BEHAVIOR_CLASSES = frozenset({
    EvidenceClass.BEHAVIORAL,
    EvidenceClass.ADVERSARIAL,
    EvidenceClass.INTEGRATION,
})


@dataclass(frozen=True)
class EvidenceClaim:
    name: str
    evidence_classes: tuple[EvidenceClass, ...]
    behavior_claimed: bool = False
    security_claimed: bool = False

    def is_sufficient(self) -> bool:
        classes = set(self.evidence_classes)
        if self.behavior_claimed and not classes.intersection(CERTIFYING_BEHAVIOR_CLASSES):
            return False
        if self.security_claimed and EvidenceClass.ADVERSARIAL not in classes:
            return False
        return True


def claim_is_sufficient(
    name: str,
    evidence_classes: Iterable[EvidenceClass | str],
    *,
    behavior_claimed: bool = False,
    security_claimed: bool = False,
) -> bool:
    normalized = tuple(EvidenceClass(value) for value in evidence_classes)
    return EvidenceClaim(
        name=name,
        evidence_classes=normalized,
        behavior_claimed=behavior_claimed,
        security_claimed=security_claimed,
    ).is_sufficient()


__all__ = [
    "EvidenceClass",
    "EvidenceClaim",
    "CERTIFYING_BEHAVIOR_CLASSES",
    "claim_is_sufficient",
]
