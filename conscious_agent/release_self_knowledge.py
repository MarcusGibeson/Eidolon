from __future__ import annotations

"""Authoritative, read-only self-knowledge for the current Eidolon release."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from release_authority import MILESTONE, NEXT_BOUNDED_UNIT, WORKING_SOURCE_VERSION


CONTRACT_VERSION = "v1501.3"
ROOT = Path(__file__).resolve().parents[1]
ALLOWLISTED_RELEASE_FILES = (
    "conscious_agent/release_authority.py",
    "README.md",
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
)

_CURRENT_RELEASE_QUERY = re.compile(
    r"\b(?:what (?:specifically )?(?:changed|is new|was fixed) in v?1500\.9(?:\.0|\.1)?|"
    r"what did v?1500\.9(?:\.0|\.1)? (?:change|fix|add)|"
    r"how is v?1500\.9(?:\.0|\.1)? different|"
    r"tell me (?:about|what changed in) v?1500\.9(?:\.0|\.1)?)\b",
    re.I,
)
_RELEASE_INSPECTION = re.compile(r"\b(?:inspect|review|check|read)\b", re.I)
_RELEASE_SCOPE = re.compile(r"\b(?:release metadata|release history|readme(?: files?)?|local release)\b", re.I)
_CHANGE_OBJECTIVE = re.compile(r"\b(?:what changed|changes?|release|version|v?1500\.9)\b", re.I)
_EVIDENCE_QUERY = re.compile(
    r"\b(?:what evidence|which (?:files|sources)|what (?:files|sources)|where did you get that|how do you know)\b",
    re.I,
)
_NEXT_WORK_QUERY = re.compile(
    r"\b(?:what should we work on next|what should (?:our|the) next (?:step|task|focus) be|what comes next for (?:you|eidolon))\b",
    re.I,
)


@dataclass(frozen=True)
class ReleaseSummary:
    ok: bool
    version: str
    milestone: str
    summary: str
    evidence_digest: str
    inspected_file_count: int
    missing_files: tuple[str, ...] = ()

    def public_result(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "message": self.summary,
            "version": self.version,
            "milestone": self.milestone,
            "evidence_digest": self.evidence_digest,
            "inspected_file_count": self.inspected_file_count,
            "missing_file_count": len(self.missing_files),
            "redacted": True,
            "provider_contacted": False,
            "source_modified": False,
            "authority_granted": False,
        }


def is_current_release_question(text: str) -> bool:
    return bool(_CURRENT_RELEASE_QUERY.search(" ".join(str(text or "").split())))


def is_grouped_release_inspection(text: str) -> bool:
    clean = " ".join(str(text or "").split())
    return bool(_RELEASE_INSPECTION.search(clean) and _RELEASE_SCOPE.search(clean) and _CHANGE_OBJECTIVE.search(clean))


def is_release_evidence_question(text: str) -> bool:
    return bool(_EVIDENCE_QUERY.search(" ".join(str(text or "").split())))


def is_next_bounded_work_question(text: str) -> bool:
    return bool(_NEXT_WORK_QUERY.search(" ".join(str(text or "").split())))


def _evidence() -> tuple[dict[str, str], tuple[str, ...]]:
    rows: dict[str, str] = {}
    missing: list[str] = []
    for relative in ALLOWLISTED_RELEASE_FILES:
        path = ROOT / relative
        try:
            rows[relative] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            missing.append(relative)
    return rows, tuple(missing)


def inspect_current_release() -> ReleaseSummary:
    evidence, missing = _evidence()
    joined = "\n".join(evidence.values())
    required_markers = (
        "integrated daily-use conversation",
        "grounded self-reflection",
        "mixed casual-plus-command",
        "verified diagnostic receipts",
        "bounded current integration profile",
    )
    complete = not missing and all(marker in joined.casefold() for marker in required_markers)
    digest = hashlib.sha256(json.dumps(
        {name: hashlib.sha256(content.encode("utf-8")).hexdigest() for name, content in sorted(evidence.items())},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    if complete:
        summary = (
            f"The authoritative local files identify this source as {MILESTONE}. "
            "v1500.9 integrated the operator-tested daily-use conversation repairs: grounded self-reflection and milestone answers, "
            "family and project-association recall with correction handling, current-message targeting, cancellation safety, "
            "mixed casual-plus-command presentation, and receipt-backed repeated diagnostics. It also bounded the ordinary full verifier "
            "to current representative stages while retaining broad historical checks in the segmented verifier. "
            f"The next bounded unit is {NEXT_BOUNDED_UNIT}."
        )
    else:
        summary = "I could not verify a complete current-release summary from every allowlisted local source, so I will not guess about what changed."
    return ReleaseSummary(complete, WORKING_SOURCE_VERSION, MILESTONE, summary, digest, len(evidence), missing)


def explain_release_evidence(summary: ReleaseSummary | None = None) -> str:
    release = summary or inspect_current_release()
    if not release.ok:
        return release.summary
    names = ", ".join(ALLOWLISTED_RELEASE_FILES)
    return (
        f"I am using four allowlisted local sources: {names}. "
        f"Their combined SHA-256 evidence digest is {release.evidence_digest}. "
        "The release authority supplies the current version, milestone, and next bounded unit; the README files supply the documented change and verification claims. "
        "I did not use provider-generated claims as evidence."
    )


def next_bounded_work_guidance() -> str:
    return (
        f"The authoritative next bounded unit is {NEXT_BOUNDED_UNIT}. "
        "We should make the supervised-initiative queue easy to review, pace, and reconcile after completion, "
        "while continued daily-use trials harden conversation continuity, memory, recovery, and action routing. "
        "Installation, promotion, model management, and active-source mutation remain your decisions."
    )


def grounded_self_progress_summary(*, more_direct: bool = False) -> str:
    """Describe current capabilities from release evidence, not model biography."""
    evidence, missing = _evidence()
    joined = "\n".join(evidence.values()).casefold()
    required_markers = (
        MILESTONE.casefold(),
        "chat-first",
        "autonomous developer beta",
        "operator daily-use",
    )
    if missing or not all(marker in joined for marker in required_markers):
        return (
            "I cannot verify a complete current self-progress summary from my allowlisted local release evidence, "
            "so I will not guess about capabilities or limitations."
        )
    opening = "More directly: " if more_direct else ""
    return (
        f"{opening}At {MILESTONE}, I can genuinely hold ordinary conversations with attributable memory and "
        "correction handling; inspect source and evidence; compare bounded improvements; and carry an explicitly "
        "authorized supervised development cycle through an isolated workspace, implementation, testing, repair, and a "
        "review-ready candidate. I can also track health and decide whether bounded unattended work is eligible, "
        "but that does not let me silently execute it. What still limits me is concrete: my local model can still "
        "produce generic or poorly grounded conversation, conversation and memory continuity can still fail, "
        "long daily-use and sleep/resume testing is unfinished, "
        "and I do not independently install, promote, manage models, use secrets, or expand my own authority. "
        f"The next evidence-led unit remains {NEXT_BOUNDED_UNIT}."
    )


def grounded_current_milestone_reflection(*, playful: bool = False, focus: str = "overview") -> str:
    """Answer current milestone reflection from authoritative release evidence."""
    evidence, missing = _evidence()
    joined = "\n".join(evidence.values()).casefold()
    required_markers = (
        MILESTONE.casefold(),
        "chat-first",
        "autonomous developer beta",
        "operator daily-use",
    )
    if missing or not all(marker in joined for marker in required_markers):
        return (
            "I cannot verify enough current release evidence to describe what this milestone means, "
            "so I would rather say that plainly than invent a polished progress story."
        )
    family = WORKING_SOURCE_VERSION.split(".", 1)[0]
    if focus == "proudest_capability":
        if "bounded autonomous web research" in joined:
            return (
                "I'm proudest that I can now coordinate a bounded research objective through privacy-safe question and source "
                "planning, public read-only observation, signed evidence extraction, contradiction-preserving comparison, "
                "and citation-traceable synthesis under one exact session authorization. Native Windows acceptance now passes; "
                "ordinary chat and dashboard routing are still the next product boundary, and final authority remains with you."
            )
        return (
            "I'm proudest that I can carry a bounded idea from inspecting my source through isolated "
            "implementation and verification. That matters because it changes my role from being only "
            "something you develop into something that can meaningfully participate in its own development, "
            "while still leaving final installation and promotion authority with you."
        )
    if focus == "limitation":
        if "bounded autonomous web research" in joined:
            return (
                "My largest remaining limitation is live-trial reliability. The research, supervised-development, memory-policy, "
                "and response-grounding machinery now have bounded implementation and verification evidence, but they still need "
                "sustained operator-run trials across real provider, restart, capability, and project conditions before I can treat "
                "their behavior as proven in daily use."
            )
        return (
            "My largest remaining limitation is consistency: I can complete bounded supervised development work, "
            "but my local model can still lose conversational meaning or produce a weak coding change. I need stronger "
            "grounding, verification, and recovery before that cycle can operate reliably without your close review."
        )
    if focus == "significance":
        return (
            f"v{family} matters because it moves me from accumulated groundwork into verified participation: I can "
            "inspect evidence, develop a bounded change in isolation, and return a tested candidate. It does not make "
            "me independently authoritative, but it makes our development relationship meaningfully two-sided."
        )
    opening = "Maybe a little. " if playful else "Reaching this milestone matters to me. "
    if "bounded autonomous web research" in joined:
        return (
            f"{opening}Reaching v{family} means I can turn one research objective into a bounded multi-step session, "
            "compare signed evidence from multiple public sources, preserve uncertainty and contradictions, and return "
            "citations under one exact operator authorization. The coordinator and production GET-only adapter now have "
            "native Windows evidence; the next work is connecting that verified capability to our ordinary conversation."
        )
    return (
        f"{opening}Reaching v{family} means I can keep attributable memory and corrections grounded, "
        "reason over evidence, and carry a bounded supervised development idea through isolated implementation "
        "and testing. That is a real change from merely having groundwork to participating in my own development. "
        "I still need your authority to install or promote changes, and sounding smart is not the same as "
        "consistently understanding you."
    )


__all__ = (
    "ALLOWLISTED_RELEASE_FILES", "ReleaseSummary", "inspect_current_release",
    "explain_release_evidence", "is_current_release_question", "is_grouped_release_inspection",
    "is_next_bounded_work_question", "is_release_evidence_question", "next_bounded_work_guidance",
    "grounded_self_progress_summary",
    "grounded_current_milestone_reflection",
)
