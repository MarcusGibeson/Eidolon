from __future__ import annotations

"""Transactional review and installation for isolated self-development candidates."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from datetime import datetime, timezone
from typing import Any, Mapping

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from supervised_self_development_contract import SOURCE_ONLY_IGNORED_PARTS


CONTRACT_VERSION = "v1501.1"
PROPOSAL_ID_PATTERN = re.compile(r"^improvement-[a-f0-9]{20}$")
MAX_INSTALL_FILES = 12


def is_candidate_review_installation_control(message: str) -> bool:
    text = str(message or "").strip()
    candidate = r"improvement-[a-f0-9]{20}"
    patterns = (
        rf"Review (?:self-development )?candidate {candidate}[.!?]*",
        rf"Install reviewed candidate {candidate} review [a-f0-9]{{16}}[.!?]*",
        rf"Review and install (?:self-development )?candidate {candidate}[.!?]*",
    )
    return any(re.fullmatch(pattern, text, re.IGNORECASE) for pattern in patterns)


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _runtime_root() -> Path:
    return Path(os.environ.get("EIDOLON_DATA_DIR") or "data").expanduser().resolve()


def _proposal_path(proposal_id: str) -> Path:
    normalized = str(proposal_id or "").lower()
    if not PROPOSAL_ID_PATTERN.fullmatch(normalized):
        raise ValueError("candidate_id_invalid")
    return _runtime_root() / "self_development_proposals" / f"{normalized}.json"


def _safe_relative_path(value: str) -> Path:
    relative = Path(str(value or "").replace("\\", "/"))
    if not value or relative.is_absolute() or ".." in relative.parts:
        raise ValueError("candidate_path_invalid")
    if any(part.casefold() in SOURCE_ONLY_IGNORED_PARTS for part in relative.parts):
        raise ValueError("candidate_path_private")
    if relative.suffix.casefold() in {".pyc", ".pyo", ".log", ".zip", ".json"}:
        raise ValueError("candidate_path_not_source_only")
    return relative


def _candidate_workspace(proposal_id: str) -> Path:
    return _runtime_root() / "self_development_proposals" / "workspaces" / proposal_id / "Eidolon"


def _candidate_rows(proposal: Mapping[str, Any], source_root: Path) -> list[dict[str, Any]]:
    result = dict(proposal.get("implementation_result") or {})
    if proposal.get("state") not in {"isolated_implementation_review_ready", "operator_installed"}:
        raise ValueError("candidate_not_review_ready")
    if result.get("checks_passed") is not True or not result.get("check_receipts"):
        raise ValueError("candidate_verification_missing")
    if not all(row.get("passed") is True for row in result.get("check_receipts") or []):
        raise ValueError("candidate_verification_failed")
    change_rows = list(result.get("change_review") or [])
    if not 0 < len(change_rows) <= MAX_INSTALL_FILES:
        raise ValueError("candidate_change_count_invalid")
    if int(result.get("changed_file_count") or 0) != len(change_rows):
        raise ValueError("candidate_change_count_mismatch")

    proposal_id = str(proposal.get("proposal_id") or "")
    workspace = _candidate_workspace(proposal_id)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    installed = proposal.get("state") == "operator_installed"
    for change in change_rows:
        relative = _safe_relative_path(str(change.get("relative_path") or ""))
        relative_text = relative.as_posix()
        if relative_text in seen:
            raise ValueError("candidate_change_path_duplicate")
        seen.add(relative_text)
        candidate_path = (workspace / relative).resolve()
        active_path = (source_root / relative).resolve()
        if workspace not in candidate_path.parents or source_root not in active_path.parents:
            raise ValueError("candidate_path_escape")
        expected_after = str(change.get("after_digest") or "")
        expected_before = str(change.get("before_digest") or "")
        if not candidate_path.is_file() or _file_digest(candidate_path) != expected_after:
            raise ValueError("candidate_workspace_digest_mismatch")
        if relative.suffix.casefold() == ".py":
            compile(candidate_path.read_bytes(), relative_text, "exec")
        active_digest = _file_digest(active_path) if active_path.is_file() else ""
        required_active_digest = expected_after if installed else expected_before
        if active_digest != required_active_digest:
            raise ValueError("active_candidate_target_drift")
        rows.append(
            {
                "relative_path": relative_text,
                "candidate_path": candidate_path,
                "active_path": active_path,
                "before_digest": expected_before,
                "after_digest": expected_after,
                "action": str(change.get("action") or "modify"),
            }
        )
    return rows


def _public_failure(proposal_id: str, reason: str) -> dict[str, Any]:
    return {
        "active": True,
        "event": "candidate_review_or_install_blocked",
        "conversation_response": (
            f"Candidate {proposal_id} was not installed. The governed review stopped at {reason}. "
            "Active source was left unchanged."
        ),
        "blocker": reason,
        "provider_contacted": False,
        "source_modified": False,
        "authority_granted": False,
    }


def review_isolated_candidate(proposal_id: str, *, source_root: str | Path) -> dict[str, Any]:
    root = Path(source_root).expanduser().resolve()
    path = _proposal_path(proposal_id)
    with metadata_mutation_lock(path, timeout_seconds=5):
        proposal = load_json_file(path, {}, expected_type=dict)
        if not proposal:
            return _public_failure(proposal_id, "candidate_not_found")
        if proposal.get("state") == "operator_installed":
            return {
                "active": True,
                "event": "candidate_installation_replayed",
                "conversation_response": (
                    f"Candidate {proposal_id} was already reviewed and installed. I did not repeat the review or modify source."
                ),
                "provider_contacted": False,
                "source_modified": False,
                "authority_granted": False,
                "self_development_proposal": proposal,
            }
        try:
            rows = _candidate_rows(proposal, root)
        except (OSError, SyntaxError, ValueError) as error:
            return _public_failure(proposal_id, str(error))
        review = {
            "contract_version": CONTRACT_VERSION,
            "proposal_id": proposal_id,
            "proposal_digest": str(proposal.get("proposal_digest") or ""),
            "implementation_result_digest": str(proposal.get("implementation_result_digest") or ""),
            "verification_digest": str(proposal.get("verification_digest") or ""),
            "reviewed_files": {row["relative_path"]: row["after_digest"] for row in rows},
            "active_target_baseline": {row["relative_path"]: row["before_digest"] for row in rows},
            "changed_file_count": len(rows),
            "checks_passed": True,
            "source_syntax_checked": True,
            "installation_executed": False,
            "provider_contacted": False,
            "content_free": True,
        }
        review["review_digest"] = _digest(review)
        updated = dict(proposal)
        updated.update(
            {
                "candidate_review": review,
                "candidate_review_digest": review["review_digest"],
                "operator_review_completed": True,
                "installation_authorized": False,
                "source_modified": False,
            }
        )
        write_json_atomic(path, updated, expected_type=dict, sort_keys=True, coordinate=False)
        phrase = f"Install reviewed candidate {proposal_id} review {review['review_digest'][:16]}."
        return {
            "active": True,
            "event": "candidate_review_ready_for_installation",
            "conversation_response": (
                f"I reviewed candidate {proposal_id}: {len(rows)} bounded source files match the isolated receipt, "
                f"all recorded verification checks passed, Python syntax is valid, and active targets have not drifted. "
                f"Nothing was installed. To install this exact review, say: {phrase}"
            ),
            "review_digest": review["review_digest"],
            "installation_phrase": phrase,
            "provider_contacted": False,
            "runtime_mutated": True,
            "source_modified": False,
            "authority_granted": False,
            "self_development_proposal": updated,
        }


def install_reviewed_candidate(
    proposal_id: str,
    *,
    source_root: str | Path,
    expected_review_digest: str = "",
    combined_review_and_install: bool = False,
) -> dict[str, Any]:
    root = Path(source_root).expanduser().resolve()
    path = _proposal_path(proposal_id)
    if combined_review_and_install:
        reviewed = review_isolated_candidate(proposal_id, source_root=root)
        if reviewed.get("event") == "candidate_installation_replayed":
            return reviewed
        if reviewed.get("event") != "candidate_review_ready_for_installation":
            return reviewed
        expected_review_digest = str(reviewed.get("review_digest") or "")

    with metadata_mutation_lock(path, timeout_seconds=5):
        proposal = load_json_file(path, {}, expected_type=dict)
        if not proposal:
            return _public_failure(proposal_id, "candidate_not_found")
        if proposal.get("state") == "operator_installed":
            return {
                "active": True,
                "event": "candidate_installation_replayed",
                "conversation_response": f"Candidate {proposal_id} is already installed. I did not modify source again.",
                "provider_contacted": False,
                "source_modified": False,
                "authority_granted": False,
                "self_development_proposal": proposal,
            }
        review = dict(proposal.get("candidate_review") or {})
        stored_review_digest = str(proposal.get("candidate_review_digest") or "")
        review_basis = {key: value for key, value in review.items() if key != "review_digest"}
        if (
            not review
            or stored_review_digest != str(review.get("review_digest") or "")
            or _digest(review_basis) != stored_review_digest
        ):
            return _public_failure(proposal_id, "candidate_review_required")
        if not combined_review_and_install and not expected_review_digest:
            return _public_failure(proposal_id, "candidate_review_digest_required")
        if expected_review_digest and not stored_review_digest.startswith(expected_review_digest.lower()):
            return _public_failure(proposal_id, "candidate_review_digest_mismatch")
        try:
            rows = _candidate_rows(proposal, root)
        except (OSError, SyntaxError, ValueError) as error:
            return _public_failure(proposal_id, str(error))

        backup_root = _runtime_root() / "self_development_proposals" / "install_backups" / proposal_id / stored_review_digest[:16]
        backup_root.mkdir(parents=True, exist_ok=True)
        installed: list[dict[str, Any]] = []
        try:
            for row in rows:
                active_path = row["active_path"]
                backup_path = backup_root / row["relative_path"]
                if active_path.is_file():
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(active_path, backup_path)
                active_path.parent.mkdir(parents=True, exist_ok=True)
                descriptor, temporary_name = tempfile.mkstemp(prefix=f".{active_path.name}.install-", dir=active_path.parent)
                try:
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(row["candidate_path"].read_bytes())
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temporary_name, active_path)
                finally:
                    if os.path.exists(temporary_name):
                        os.unlink(temporary_name)
                installed.append(row)
                if _file_digest(active_path) != row["after_digest"]:
                    raise OSError("installed_candidate_digest_mismatch")
        except Exception as error:
            for row in reversed(installed):
                backup_path = backup_root / row["relative_path"]
                if backup_path.is_file():
                    shutil.copy2(backup_path, row["active_path"])
                elif not row["before_digest"] and row["active_path"].exists():
                    row["active_path"].unlink()
            return _public_failure(proposal_id, f"transaction_rolled_back:{type(error).__name__}")

        installation = {
            "contract_version": CONTRACT_VERSION,
            "proposal_id": proposal_id,
            "proposal_digest": str(proposal.get("proposal_digest") or ""),
            "review_digest": stored_review_digest,
            "installed_files": {row["relative_path"]: row["after_digest"] for row in rows},
            "installed_file_count": len(rows),
            "backup_manifest": {
                row["relative_path"]: (_file_digest(backup_root / row["relative_path"]) if (backup_root / row["relative_path"]).is_file() else "new_file")
                for row in rows
            },
            "installation_completed": True,
            "provider_contacted": False,
            "promotion_authorized": False,
            "content_free": True,
        }
        installation["installation_digest"] = _digest(installation)
        installed_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        completed = dict(proposal)
        completed.update(
            {
                "state": "operator_installed",
                "installed_at": installed_at,
                "operator_installed": True,
                "operator_review_completed": True,
                "installation_authorized": True,
                "installation_completed": True,
                "source_modified": True,
                "promotion_authorized": False,
                "installation_result": installation,
                "installation_digest": installation["installation_digest"],
            }
        )
        write_json_atomic(path, completed, expected_type=dict, sort_keys=True, coordinate=False)
        initiative_reconciliation: dict[str, Any] = {}
        if completed.get("dynamic_candidate_id") and completed.get("evidence_digest"):
            from supervised_initiative_queue import update_supervised_initiative_lifecycle

            initiative_reconciliation = update_supervised_initiative_lifecycle(
                str(completed.get("dynamic_candidate_id")),
                str(completed.get("evidence_digest")),
                "operator_installed",
                proposal_id=proposal_id,
                runtime_root=_runtime_root(),
            )
        return {
            "active": True,
            "event": "candidate_operator_installation_completed",
            "conversation_response": (
                f"I reviewed and installed candidate {proposal_id}. {len(rows)} bounded source files were applied "
                f"transactionally, their installed digests match, and rollback copies remain outside active source. "
                "No provider or promotion action ran. Restart Eidolon before relying on changed runtime code."
            ),
            "installation_digest": installation["installation_digest"],
            "provider_contacted": False,
            "runtime_mutated": True,
            "source_modified": True,
            "authority_granted": False,
            "initiative_reconciliation": initiative_reconciliation,
            "self_development_proposal": completed,
        }


__all__ = [
    "CONTRACT_VERSION",
    "install_reviewed_candidate",
    "is_candidate_review_installation_control",
    "review_isolated_candidate",
]
