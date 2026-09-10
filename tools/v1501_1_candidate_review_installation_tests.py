from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "conscious_agent")]

from checkpoint_registry import checkpoint_registry_manifest
from dashboard_chat_console import _propose_explicit_chat_action
from supervised_candidate_installation import install_reviewed_candidate, review_isolated_candidate
from v1489_product_capability_integration import integrate_v1489_product_capabilities


CHECKS: list[str] = []


def require(condition: object, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    CHECKS.append(label)


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def source_signature() -> str:
    rows = []
    for path in sorted((ROOT / "conscious_agent").glob("*.py")):
        rows.append((path.name, digest_bytes(path.read_bytes())))
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def seed_candidate(base: Path, proposal_id: str, *, bad_path: bool = False) -> tuple[Path, Path, bytes]:
    source = base / "active" / "Eidolon"
    runtime = base / "runtime"
    relative = Path("data/private.py") if bad_path else Path("conscious_agent/sample_feature.py")
    active = source / relative
    active.parent.mkdir(parents=True, exist_ok=True)
    before = b"def value():\n    return 'before'\n"
    after = b"def value():\n    return 'after'\n"
    active.write_bytes(before)
    workspace = runtime / "self_development_proposals" / "workspaces" / proposal_id / "Eidolon"
    candidate = workspace / relative
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_bytes(after)
    proposal = {
        "proposal_id": proposal_id,
        "proposal_digest": "a" * 64,
        "state": "isolated_implementation_review_ready",
        "verification_digest": "b" * 64,
        "implementation_result_digest": "c" * 64,
        "implementation_result": {
            "checks_passed": True,
            "check_receipts": [{"check_index": 1, "passed": True, "return_code": 0}],
            "changed_file_count": 1,
            "changed_files": [relative.as_posix()],
            "change_review": [
                {
                    "relative_path": relative.as_posix(),
                    "action": "modify",
                    "before_digest": digest_bytes(before),
                    "after_digest": digest_bytes(after),
                }
            ],
        },
        "source_modified": False,
        "installation_authorized": False,
        "promotion_authorized": False,
    }
    proposal_path = runtime / "self_development_proposals" / f"{proposal_id}.json"
    proposal_path.parent.mkdir(parents=True, exist_ok=True)
    proposal_path.write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    return source, runtime, after


before_source = source_signature()
old_runtime = os.environ.get("EIDOLON_DATA_DIR")
temporary = Path(tempfile.mkdtemp(prefix="eidolon-v1501-1-"))
try:
    proposal_id = "improvement-11111111111111111111"
    source, runtime, expected = seed_candidate(temporary / "review-install", proposal_id)
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)

    reviewed = review_isolated_candidate(proposal_id, source_root=source)
    require(reviewed.get("event") == "candidate_review_ready_for_installation", "candidate_review_ready")
    require(reviewed.get("source_modified") is False, "review_does_not_modify_source")
    require((source / "conscious_agent/sample_feature.py").read_text().endswith("'before'\n"), "active_source_unchanged_after_review")
    require(str(reviewed.get("installation_phrase") or "").startswith("Install reviewed candidate"), "review_returns_exact_install_phrase")

    wrong = install_reviewed_candidate(proposal_id, source_root=source, expected_review_digest="0" * 16)
    require(wrong.get("blocker") == "candidate_review_digest_mismatch", "wrong_review_digest_blocked")
    require(wrong.get("source_modified") is False, "wrong_digest_preserves_source")

    installed = install_reviewed_candidate(
        proposal_id,
        source_root=source,
        expected_review_digest=str(reviewed["review_digest"])[:16],
    )
    require(installed.get("event") == "candidate_operator_installation_completed", "reviewed_candidate_installed")
    require((source / "conscious_agent/sample_feature.py").read_bytes() == expected, "installed_bytes_match_candidate")
    require(installed.get("provider_contacted") is False, "installation_contacts_no_provider")
    require(installed.get("authority_granted") is False, "installation_grants_no_future_authority")
    require((runtime / "self_development_proposals/install_backups" / proposal_id).is_dir(), "rollback_copy_created_externally")

    replay = install_reviewed_candidate(
        proposal_id,
        source_root=source,
        expected_review_digest=str(reviewed["review_digest"])[:16],
    )
    require(replay.get("event") == "candidate_installation_replayed", "duplicate_install_replays_receipt")
    require(replay.get("source_modified") is False, "duplicate_install_does_not_rewrite_source")

    combined_id = "improvement-22222222222222222222"
    combined_source, combined_runtime, combined_expected = seed_candidate(temporary / "combined", combined_id)
    os.environ["EIDOLON_DATA_DIR"] = str(combined_runtime)
    combined = integrate_v1489_product_capabilities(
        f"Review and install candidate {combined_id}.", {}, source_root=combined_source
    )
    require(combined.get("event") == "candidate_operator_installation_completed", "combined_conversation_command_installs")
    require((combined_source / "conscious_agent/sample_feature.py").read_bytes() == combined_expected, "combined_install_matches_candidate")

    review_only_id = "improvement-33333333333333333333"
    review_source, review_runtime, _ = seed_candidate(temporary / "review-only", review_only_id)
    os.environ["EIDOLON_DATA_DIR"] = str(review_runtime)
    routed_review = integrate_v1489_product_capabilities(
        f"Review candidate {review_only_id}.", {}, source_root=review_source
    )
    require(routed_review.get("event") == "candidate_review_ready_for_installation", "review_command_routes_without_provider")
    routed_install = integrate_v1489_product_capabilities(
        routed_review["installation_phrase"], {}, source_root=review_source
    )
    require(routed_install.get("event") == "candidate_operator_installation_completed", "exact_install_command_routes")
    require(
        _propose_explicit_chat_action(f"Review and install candidate {review_only_id}.", "") is None,
        "dashboard_pre_provider_router_defers_candidate_control",
    )

    drift_id = "improvement-44444444444444444444"
    drift_source, drift_runtime, _ = seed_candidate(temporary / "drift", drift_id)
    os.environ["EIDOLON_DATA_DIR"] = str(drift_runtime)
    (drift_source / "conscious_agent/sample_feature.py").write_text("def value():\n    return 'operator edit'\n", encoding="utf-8")
    drifted = review_isolated_candidate(drift_id, source_root=drift_source)
    require(drifted.get("blocker") == "active_candidate_target_drift", "operator_edit_blocks_review")

    private_id = "improvement-55555555555555555555"
    private_source, private_runtime, _ = seed_candidate(temporary / "private", private_id, bad_path=True)
    os.environ["EIDOLON_DATA_DIR"] = str(private_runtime)
    private = review_isolated_candidate(private_id, source_root=private_source)
    require(private.get("blocker") == "candidate_path_private", "private_runtime_path_blocked")

    manifest = checkpoint_registry_manifest(source_root=ROOT)
    require(manifest.get("ok") is True, "checkpoint_registry_recent_selectors_coherent")
    require(not manifest.get("errors"), "checkpoint_registry_has_no_resolution_errors")
    require(source_signature() == before_source, "suite_preserves_authoritative_source")

    print(
        json.dumps(
            {
                "ok": True,
                "passed": len(CHECKS),
                "failed": 0,
                "checks": CHECKS,
                "suite": "v1501.1-candidate-review-installation",
                "provider_contacted": False,
                "authoritative_source_modified": False,
            },
            indent=2,
        )
    )
finally:
    if old_runtime is None:
        os.environ.pop("EIDOLON_DATA_DIR", None)
    else:
        os.environ["EIDOLON_DATA_DIR"] = old_runtime
    shutil.rmtree(temporary, ignore_errors=True)
