from __future__ import annotations

"""Explicit version roles for Eidolon.

A release number, an installed project version, a candidate label, an archive
filename, historical evidence, and a metadata schema are different facts.  This
module keeps those roles separate and provides a content-free compatibility
surface for callers that previously treated every field named ``version`` as the
same authority.
"""

from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Any, Mapping

try:
    from release_metadata import METADATA_SCHEMA_VERSION, RUNTIME_MILESTONE, RUNTIME_VERSION, RUNTIME_VERSION_TAG, VERSION_ROLE_CONTRACT_VERSION, WORKING_SOURCE_VERSION
except ImportError:
    from release_metadata import (
        METADATA_SCHEMA_VERSION,
        RUNTIME_MILESTONE,
        RUNTIME_VERSION,
        RUNTIME_VERSION_TAG,
        VERSION_ROLE_CONTRACT_VERSION,
        WORKING_SOURCE_VERSION,
    )

_VERSION_TOKEN = re.compile(r"(?<!\d)v?(\d+(?:\.\d+)+)(?!\d)", re.IGNORECASE)
_ARTIFACT_VERSION_TOKEN = re.compile(r"(?<!\d)v?(\d+(?:[._]\d+)+)(?!\d)", re.IGNORECASE)
_HISTORY_HEADING = re.compile(r"^#{2,6}\s+v(\d+(?:\.\d+)+)\b", re.MULTILINE)

ROLE_WORKING_SOURCE = "working_source"
ROLE_INSTALLED = "installed"
ROLE_CANDIDATE = "candidate"
ROLE_PACKAGED_ARCHIVE = "packaged_archive"
ROLE_PROMOTED = "promoted_release"
ROLE_CERTIFIED = "certified_release"
ROLE_HISTORICAL = "historical"
ROLE_METADATA_SCHEMA = "metadata_schema"
VERSION_ROLES = (
    ROLE_WORKING_SOURCE,
    ROLE_INSTALLED,
    ROLE_CANDIDATE,
    ROLE_PACKAGED_ARCHIVE,
    ROLE_PROMOTED,
    ROLE_CERTIFIED,
    ROLE_HISTORICAL,
    ROLE_METADATA_SCHEMA,
)


def normalize_version(value: Any) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    match = _VERSION_TOKEN.search(token)
    return match.group(1) if match else ""


def version_from_artifact_name(name: str | Path | None) -> str:
    token = Path(str(name or "")).name
    match = _ARTIFACT_VERSION_TOKEN.search(token)
    return match.group(1).replace("_", ".") if match else ""


def authoritative_working_source_version() -> str:
    """Return the sole current source/runtime version authority."""
    return WORKING_SOURCE_VERSION


def _history_versions(root: Path) -> list[str]:
    path = root / "README_RELEASE_HISTORY.md"
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return []
    values: list[str] = []
    seen: set[str] = set()
    for value in _HISTORY_HEADING.findall(text):
        if value not in seen:
            seen.add(value)
            values.append(value)
    return values


def _settings_schema(root: Path) -> str:
    path = root / "data" / "settings.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("settings_version") or payload.get("schema_version") or "").strip()


def _role(
    role: str,
    version: str,
    *,
    status: str,
    source: str,
    authoritative: bool,
    mutable: bool,
    claim: str,
) -> dict[str, Any]:
    return {
        "role": role,
        "version": version,
        "status": status,
        "source": source,
        "authoritative": bool(authoritative),
        "mutable": bool(mutable),
        "claim": claim,
    }


def build_version_role_contract(
    root_dir: str | Path | None = None,
    *,
    installed_version: str = "",
    candidate_version: str = "",
    candidate_name: str = "",
    packaged_archive_name: str = "",
    promoted_version: str = "",
    certified_version: str = "",
) -> dict[str, Any]:
    root = Path(root_dir or Path(__file__).resolve().parents[1]).resolve()
    working = authoritative_working_source_version()
    installed = normalize_version(installed_version)
    # Candidate identity must come from an explicit frozen-candidate record.
    # A filename, candidate-like label, or merely existing ZIP is not evidence.
    candidate = normalize_version(candidate_version)
    packaged = version_from_artifact_name(packaged_archive_name)
    promoted = normalize_version(promoted_version)
    certified = normalize_version(certified_version)
    history = _history_versions(root)
    settings_schema = _settings_schema(root)

    rows = [
        _role(
            ROLE_WORKING_SOURCE,
            working,
            status="current",
            source="conscious_agent/release_metadata.py:WORKING_SOURCE_VERSION",
            authoritative=True,
            mutable=False,
            claim="The source currently being executed or inspected.",
        ),
        _role(
            ROLE_INSTALLED,
            installed,
            status="declared" if installed else "unknown",
            source="explicit mutable runtime metadata" if installed else "not declared by source",
            authoritative=bool(installed),
            mutable=True,
            claim="The operator-installed project version, when explicitly supplied.",
        ),
        _role(
            ROLE_CANDIDATE,
            candidate,
            status="declared" if candidate else "not_declared",
            source="explicit frozen candidate identity" if candidate else "no frozen candidate supplied",
            authoritative=bool(candidate),
            mutable=False,
            claim="An unpromoted candidate under review.",
        ),
        _role(
            ROLE_PACKAGED_ARCHIVE,
            packaged,
            status="declared" if packaged else "not_packaged",
            source="archive filename" if packaged else "no archive supplied",
            authoritative=bool(packaged),
            mutable=False,
            claim="The version encoded in a concrete package filename.",
        ),
        _role(
            ROLE_PROMOTED,
            promoted,
            status="declared" if promoted else "unknown",
            source="explicit promotion evidence" if promoted else "no direct promotion evidence supplied",
            authoritative=bool(promoted),
            mutable=True,
            claim="The operator-promoted release, only when directly evidenced.",
        ),
        _role(
            ROLE_CERTIFIED,
            certified,
            status="declared" if certified else "unknown",
            source="explicit certification evidence" if certified else "no direct certification evidence supplied",
            authoritative=bool(certified),
            mutable=True,
            claim="The certified release, only when directly evidenced.",
        ),
        _role(
            ROLE_HISTORICAL,
            history[0] if history else "",
            status="available" if history else "unavailable",
            source="README_RELEASE_HISTORY.md headings",
            authoritative=False,
            mutable=False,
            claim="Immutable historical evidence, not current runtime authority.",
        ),
        _role(
            ROLE_METADATA_SCHEMA,
            METADATA_SCHEMA_VERSION,
            status="declared",
            source="release metadata schema authority",
            authoritative=True,
            mutable=False,
            claim="Serialization/schema compatibility, not a product release.",
        ),
    ]
    contradictions: list[dict[str, str]] = []
    if candidate and candidate != working:
        contradictions.append({"kind": "candidate_working_mismatch", "working_source": working, "candidate": candidate})
    if packaged and packaged != working:
        contradictions.append({"kind": "package_working_mismatch", "working_source": working, "packaged_archive": packaged})
    if candidate and packaged and candidate != packaged:
        contradictions.append({"kind": "candidate_package_mismatch", "candidate": candidate, "packaged_archive": packaged})

    return {
        "ok": not contradictions,
        "status": "pass" if not contradictions else "drift_detected",
        "contract_version": VERSION_ROLE_CONTRACT_VERSION,
        "working_source_version": working,
        "runtime_compatibility_version": RUNTIME_VERSION,
        "runtime_tag": RUNTIME_VERSION_TAG,
        "milestone": RUNTIME_MILESTONE,
        "installed_version": installed,
        "candidate_version": candidate,
        "packaged_archive_version": packaged,
        "promoted_release_version": promoted,
        "certified_release_version": certified,
        "metadata_schema_version": METADATA_SCHEMA_VERSION,
        "settings_schema_version": settings_schema,
        "historical_latest_version": history[0] if history else "",
        "historical_version_count": len(history),
        "roles": rows,
        "contradictions": contradictions,
        "installed_claimed_by_source": False,
        "candidate_claimed_as_installed": False,
        "candidate_inferred_from_name": False,
        "candidate_name_observed": Path(str(candidate_name or "")).name if candidate_name else "",
        "promotion_claimed_by_source": False,
        "certification_claimed_by_source": False,
        "verification_claimed_as_certification": False,
        "content_free": True,
    }


def project_version_roles(project: Mapping[str, Any] | None) -> dict[str, Any]:
    project = project or {}
    working = normalize_version(project.get("working_version") or project.get("version"))
    installed = normalize_version(project.get("installed_version"))
    candidate = normalize_version(project.get("candidate_version"))
    promoted = normalize_version(project.get("promoted_version"))
    certified = normalize_version(project.get("certified_version"))
    return {
        "installed_version": installed,
        "working_source_version": working,
        "candidate_version": candidate,
        "promoted_release_version": promoted,
        "certified_release_version": certified,
        "root_version": normalize_version(project.get("root_version")),
        "installed_status": "declared" if installed else "unknown",
        "candidate_status": "declared" if candidate else "not_declared",
        "promoted_status": "declared" if promoted else "unknown",
        "certified_status": "declared" if certified else "unknown",
        "working_status": "declared" if working else "unknown",
        "roles_separate": True,
        "content_free": True,
    }
