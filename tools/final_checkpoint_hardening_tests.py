from __future__ import annotations

"""Deterministic v1080.1 Desktop Alpha first-use stabilization checks.

This suite adds no product feature and contacts no provider. It audits current
metadata, verifier registration, duplicate/order contracts, companion-facing
presentation boundaries, keyboard/focus/layout behavior, governance, source
immutability, runtime restoration, and source-only privacy.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))
EXTERNAL_DATA_DIR = Path(os.environ.get("EIDOLON_DATA_DIR") or (ROOT / "data")).resolve()
EXPECTED_VERSION = "1080.1"
EXPECTED_TAG = "v1080.1"
EXPECTED_MILESTONE = "v1080.1 Desktop Alpha First-Use Stabilization"
EXPECTED_REPAIR_HEADING = EXPECTED_MILESTONE
EXPECTED_NEXT = "v1080.2 Desktop Alpha Soak Repairs"


def _tree_bytes(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _source_snapshot() -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in ROOT.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        relative = path.relative_to(ROOT).as_posix()
        snapshot[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def _snapshot_runtime(root: Path) -> Path:
    backup = Path(tempfile.mkdtemp(prefix="eidolon-final-hardening-runtime-"))
    if root.exists():
        shutil.copytree(root, backup / "data", dirs_exist_ok=True)
    return backup


def _restore_runtime(root: Path, backup: Path) -> None:
    if root.exists():
        shutil.rmtree(root)
    saved = backup / "data"
    if saved.exists():
        shutil.copytree(saved, root)
    shutil.rmtree(backup, ignore_errors=True)


def _check(name: str, function: Callable[[], None]) -> dict[str, Any]:
    try:
        function()
        return {"name": name, "status": "pass"}
    except Exception as error:
        return {"name": name, "status": "fail", "error": f"{type(error).__name__}: {error}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    source_before = _source_snapshot()
    runtime_before = _tree_bytes(EXTERNAL_DATA_DIR)
    backup = _snapshot_runtime(EXTERNAL_DATA_DIR)
    results: list[dict[str, Any]] = []
    restore_error = ""

    try:
        from metadata_release_integrity import (
            build_metadata_version_inventory,
            build_project_workspace_metadata_alignment,
        )
        from package_integrity import (
            forbidden_runtime_path_matches,
            iter_source_tree_entries,
            privacy_deep_scan_summary,
        )
        from release_metadata import (
            NEXT_RECOMMENDED_ARC,
            PREVIOUS_RUNTIME_VERSION,
            RUNTIME_MILESTONE,
            RUNTIME_VERSION,
            RUNTIME_VERSION_TAG,
        )
        from source_package_privacy_metadata_integrity import (
            build_source_package_privacy_metadata_integrity_audit,
        )

        dashboard = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
        navigation = (AGENT / "conversation_navigation.py").read_text(encoding="utf-8")
        operations = (AGENT / "conversation_operations.py").read_text(encoding="utf-8")
        sessions = (AGENT / "conversation_sessions.py").read_text(encoding="utf-8")
        verifier = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
        history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        operator_guide = (ROOT / "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md").read_text(encoding="utf-8")

        def release_metadata_is_final_candidate() -> None:
            assert RUNTIME_VERSION == EXPECTED_VERSION
            assert RUNTIME_VERSION_TAG == EXPECTED_TAG
            assert RUNTIME_MILESTONE == EXPECTED_MILESTONE
            assert NEXT_RECOMMENDED_ARC == EXPECTED_NEXT
            assert PREVIOUS_RUNTIME_VERSION == "1080.0"

        def packaged_metadata_is_aligned() -> None:
            inventory = build_metadata_version_inventory(ROOT)
            alignment = build_project_workspace_metadata_alignment(ROOT)
            assert inventory.get("ok") is True, inventory.get("blocked")
            assert alignment.get("ok") is True, alignment.get("blocked")

        def privacy_metadata_audit_is_current_and_non_authorizing() -> None:
            report = build_source_package_privacy_metadata_integrity_audit(ROOT)
            assert report.get("ok") is True
            assert report.get("authorizes_package_creation") is False
            assert report.get("publishes_release") is False
            assert report.get("expands_autonomy") is False

        def docs_are_current_and_history_is_preserved() -> None:
            assert readme.startswith(f"# Eidolon {EXPECTED_REPAIR_HEADING}")
            assert next_steps.startswith(f"# {EXPECTED_REPAIR_HEADING}")
            assert history.startswith(f"# {EXPECTED_REPAIR_HEADING}")
            for heading in ("## Side-by-side setup", "## Backup and upgrade", "## Rollback", "## Known limitations"):
                assert heading in operator_guide
            assert "Never run two versions against the same writable data directory at the same time." in operator_guide
            setup_ps = (ROOT / "setup.ps1").read_text(encoding="utf-8")
            setup_sh = (ROOT / "setup.sh").read_text(encoding="utf-8")
            assert '("3.11", "3.12", "3.13", "3.14")' in setup_ps
            assert "python3.11 python3.12 python3.13 python3.14" in setup_sh
            assert "< (3, 15)" in setup_ps and "< (3, 15)" in setup_sh
            for historical in (
                "# v1079.5.7 Daily Companion Polish and Consolidation Development Checkpoint",
                "# v1079.5.6 Conversation Lifecycle and New-Session Continuity Development Checkpoint",
                "# v1079.4 Conversation Experience and Relationship Continuity Final",
                "# v1079.3 Conversational Runtime Reliability and Recovery Final",
            ):
                assert historical in history
            assert "unpromoted source-only first-use stabilization candidate" in next_steps.lower()
            assert "v1079.8.2 Native Conversation Validation Desktop Final" in history

        def focused_suites_are_registered_once() -> None:
            required = (
                "daily_companion_polish_consolidation_tests.py",
                "conversation_lifecycle_continuity_tests.py",
                "conversation_navigation_continuity_tests.py",
                "daily_companion_usability_tests.py",
                "inflight_turn_reconciliation_tests.py",
                "daily_reentry_cues_tests.py",
                "provider_readiness_recovery_tests.py",
                "conversation_experience_tests.py",
                "conversation_runtime_tests.py",
                "conversation_session_tests.py",
                "conversation_session_organization_tests.py",
                "conversation_arc_consolidation_tests.py",
                "final_checkpoint_hardening_tests.py",
                "reviewed_candidate_repair_tests.py",
                "multi_tab_conversation_coordination_tests.py",
                "conversational_responsiveness_companion_quality_tests.py",
                "native_conversation_validation_tests.py",
                "desktop_alpha_daily_use_hardening_tests.py",
                "desktop_alpha_first_use_stabilization_tests.py",
            )
            for suite in required:
                assert verifier.count(suite) == 1, suite

        def duplicate_and_order_contracts_remain_present() -> None:
            required_dashboard = (
                "companionActionLocks",
                "pendingSubmissions",
                "acceptanceKey",
                "selectionRequestToken",
                "nextSelectionGeneration",
                "isCurrentSelection",
                "clearAcceptedDraft",
                "resolveAcceptanceByKey",
                "pollOperation",
                "acknowledgeCurrentSessionCue",
                "performConversationLifecycle",
            )
            for token in required_dashboard:
                assert token in dashboard, token
            for token in (
                "selection_generation",
                "client_id",
                "request_key",
                "duplicate_request",
                "stale_selection_ignored",
                "stale_lifecycle_ignored",
            ):
                assert token in navigation, token
            for token in (
                "acceptance_key",
                "cancellation_requested",
                "final_session_turn_recorded",
                "operation_cue_token",
                "acknowledged_public_state",
            ):
                assert token in operations, token
            assert "clear_conversation_draft" in sessions and "cleared_at" in sessions

        def ordinary_language_and_progressive_disclosure_are_bounded() -> None:
            for label in (
                "Ready", "Saving draft", "Switching conversation", "Creating conversation",
                "Still responding", "Needs recovery", "Cancelling safely", "Cancelled safely",
                "Completion uncertain", "Offline mode", "Archiving conversation", "Restoring conversation",
            ):
                assert label in dashboard, label
            assert "chat-turn-diagnostics" in dashboard
            assert "Generation details" in dashboard
            assert "Operation" in dashboard and "Endpoint" in dashboard
            assert "This marker contains no message text" in dashboard
            assert "data-chat-version='v1080.1-desktop-alpha-stabilization'" in dashboard
            dashboard_py = (ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
            assert "v1080.1 Desktop Alpha First-Use Stabilization</strong> current smoke debt marker" in dashboard_py

        def keyboard_focus_tooltip_and_compact_layout_contracts_hold() -> None:
            assert "if (event.key !== 'Enter') return;" in dashboard
            assert "messageBox.addEventListener('beforeinput'" in dashboard
            assert "event.key !== 'Escape'" in dashboard
            assert "closeTemporaryCompanionSurfaces" in dashboard
            assert "focusComposer" in dashboard
            assert "@media (max-width:" in dashboard
            assert "data-tip=" in (ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
            assert " title=" not in dashboard.lower()
            assert " title='" not in dashboard.lower()

        def governance_remains_closed() -> None:
            combined = readme + "\n" + next_steps + "\n" + operator_guide
            for statement in (
                "not automatically installed",
                "Installation remains a separate operator decision",
                "No provider or model is switched automatically",
                "no model is installed or managed",
            ):
                assert statement.lower() in combined.lower(), statement
            assert "enable autonomous actions" not in next_steps.lower()
            assert "Desktop Alpha is supervised local software" in operator_guide

        def source_only_inventory_is_private() -> None:
            entries = iter_source_tree_entries(ROOT)
            assert not forbidden_runtime_path_matches(entries)
            items = {
                relative: (ROOT / relative).read_bytes()
                for relative in entries
                if (ROOT / relative).is_file()
            }
            summary = privacy_deep_scan_summary(items)
            assert summary.get("ok") is True, summary.get("private_content_findings")
            for forbidden in (
                "data/projects.json",
                "data/conversation_sessions/",
                "data/conversation_runtime/",
                "data/conversation_navigation/",
                "data/dashboard_chat/",
            ):
                assert all(not entry.startswith(forbidden) for entry in entries), forbidden

        def no_new_authority_or_broad_feature_surface_was_added() -> None:
            diff_sensitive = (
                AGENT / "release_metadata.py",
                AGENT / "settings_manager.py",
                AGENT / "dashboard_chat_console.py",
                ROOT / "README.md",
                ROOT / "README_NEXT_STEPS.md",
                ROOT / "README_RELEASE_HISTORY.md",
                ROOT / "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md",
                ROOT / "data" / "settings.json",
                ROOT / "data" / "workspaces" / "active_project.json",
                ROOT / "data" / "workspaces" / "projects.json",
                ROOT / "tools" / "release_verify.py",
                ROOT / "tools" / "final_checkpoint_hardening_tests.py",
            )
            assert all(path.exists() for path in diff_sensitive)
            assert "install_model(" not in dashboard
            assert "delete_model(" not in dashboard
            assert "automatic_fallback" not in dashboard

        checks = (
            ("release_metadata_is_final_candidate", release_metadata_is_final_candidate),
            ("packaged_metadata_is_aligned", packaged_metadata_is_aligned),
            ("privacy_metadata_audit_is_current_and_non_authorizing", privacy_metadata_audit_is_current_and_non_authorizing),
            ("docs_are_current_and_history_is_preserved", docs_are_current_and_history_is_preserved),
            ("focused_suites_are_registered_once", focused_suites_are_registered_once),
            ("duplicate_and_order_contracts_remain_present", duplicate_and_order_contracts_remain_present),
            ("ordinary_language_and_progressive_disclosure_are_bounded", ordinary_language_and_progressive_disclosure_are_bounded),
            ("keyboard_focus_tooltip_and_compact_layout_contracts_hold", keyboard_focus_tooltip_and_compact_layout_contracts_hold),
            ("governance_remains_closed", governance_remains_closed),
            ("source_only_inventory_is_private", source_only_inventory_is_private),
            ("no_new_authority_or_broad_feature_surface_was_added", no_new_authority_or_broad_feature_surface_was_added),
        )
        results.extend(_check(name, function) for name, function in checks)
    finally:
        try:
            _restore_runtime(EXTERNAL_DATA_DIR, backup)
        except Exception as error:
            restore_error = f"{type(error).__name__}: {error}"

    runtime_restored = not restore_error and _tree_bytes(EXTERNAL_DATA_DIR) == runtime_before
    source_unchanged = _source_snapshot() == source_before
    results.append({"name": "external_runtime_data_restored_byte_for_byte", "status": "pass" if runtime_restored else "fail", **({} if runtime_restored else {"error": restore_error or "runtime tree changed"})})
    results.append({"name": "source_tree_remains_immutable", "status": "pass" if source_unchanged else "fail", **({} if source_unchanged else {"error": "source tree changed during audit"})})

    passed = sum(item.get("status") == "pass" for item in results)
    report = {
        "suite": "v1080.1-final-checkpoint-hardening",
        "version": EXPECTED_VERSION,
        "status": "pass" if passed == len(results) else "fail",
        "ok": passed == len(results),
        "passed": passed,
        "total": len(results),
        "checks": results,
        "runtime_data_restored": runtime_restored,
        "runtime_data_restore_error": restore_error or None,
        "native_provider_contacted": False,
        "model_management_performed": False,
        "release_authorized": False,
        "desktop_review_performed": False,
        "certification_performed": False,
        "operator_promotion_performed": False,
        "evidence_kind": "deterministic development-candidate hardening audit",
    }
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{report['suite']}: {passed}/{len(results)} passed")
        for item in results:
            print(f"- {item['status']}: {item['name']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
