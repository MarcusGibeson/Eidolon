from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time
import sys

ROOT = Path(__file__).resolve().parents[1]
for item in (ROOT / "conscious_agent", ROOT / "tools"):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from v1098_bundle_a_test_support import file_snapshot, prepare_ready_fixture
from release_candidate_identity import atomic_json, digest_payload, read_json
from release_authority_readiness_recovery import refresh_release_authority_readiness
from release_authority_handoff_plan import (
    HANDOFF_ACK_CONFIRMATION,
    _record_digest,
    acknowledge_release_authority_handoff_plan,
    create_release_authority_handoff_plan,
    handoff_plan_directory,
    preview_release_authority_handoff_acknowledgment,
    release_authority_handoff_acknowledgment_status,
)
from release_authority_handoff_ack_recovery import (
    CLEANUP_CONFIRMATION,
    RECOVERY_CONFIRMATION,
    REPLACEMENT_CONFIRMATION,
    cleanup_handoff_acknowledgment_artifacts,
    handoff_acknowledgment_recovery_status,
    preview_handoff_acknowledgment_cleanup,
    preview_handoff_acknowledgment_recovery,
    preview_handoff_acknowledgment_replacement,
    recover_handoff_acknowledgment,
    replace_handoff_acknowledgment,
)
from api_server import ApiError, handle_api_get, handle_api_post


def check(name: str, ok: object) -> dict[str, object]:
    return {"name": name, "ok": bool(ok)}


def rewrite_token(runtime_root: Path, token: str, field: str, value: object) -> str:
    token_id = token.split(".", 1)[0]
    path = handoff_plan_directory(runtime_root) / "authorizations" / f"{token_id}.json"
    auth = read_json(path)
    auth[field] = value
    auth["binding_sha256"] = _record_digest(auth, "binding_sha256")
    atomic_json(path, auth)
    return f"{token_id}.{auth['binding_sha256']}.{auth['nonce']}"


def expire_active_ack(runtime_root: Path) -> tuple[str, bytes]:
    directory = handoff_plan_directory(runtime_root)
    pointer_path = directory / "active_acknowledgment.json"
    pointer = read_json(pointer_path)
    receipt_path = directory / "acknowledgments" / f"{pointer['acknowledgment_id']}.json"
    receipt = read_json(receipt_path)
    old_pointer = pointer_path.read_bytes()
    receipt["expires_at"] = "2000-01-01T00:00:00.000Z"
    receipt["receipt_sha256"] = _record_digest(receipt, "receipt_sha256")
    atomic_json(receipt_path, receipt)
    pointer["receipt_sha256"] = receipt["receipt_sha256"]
    atomic_json(pointer_path, pointer)
    return str(receipt["acknowledgment_id"]), old_pointer


def main() -> int:
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="eidolon-v1098-4-") as temp:
        fixture = prepare_ready_fixture(Path(temp))
        runtime_root = Path(fixture["runtime_root"])
        target = Path(fixture["target"])
        target_before = file_snapshot(target)
        refresh_release_authority_readiness(runtime_root=runtime_root)
        plan = create_release_authority_handoff_plan(runtime_root=runtime_root)
        rows.append(check("coherent-plan-required", plan.get("ok")))

        base = preview_release_authority_handoff_acknowledgment(
            operator_tab_id="tab-ack", operation_revision=41, runtime_root=runtime_root
        )
        wrong = acknowledge_release_authority_handoff_plan(
            base.get("authorization_token", ""), confirm="yes", operator_tab_id="tab-ack", operation_revision=41, runtime_root=runtime_root
        )
        malformed = acknowledge_release_authority_handoff_plan(
            "truthy", confirm=HANDOFF_ACK_CONFIRMATION, operator_tab_id="tab-ack", operation_revision=41, runtime_root=runtime_root
        )
        cross_tab = acknowledge_release_authority_handoff_plan(
            base.get("authorization_token", ""), confirm=HANDOFF_ACK_CONFIRMATION, operator_tab_id="tab-other", operation_revision=41, runtime_root=runtime_root
        )
        stale_revision = acknowledge_release_authority_handoff_plan(
            base.get("authorization_token", ""), confirm=HANDOFF_ACK_CONFIRMATION, operator_tab_id="tab-ack", operation_revision=40, runtime_root=runtime_root
        )
        with tempfile.TemporaryDirectory(prefix="eidolon-v1098-4-cross-") as cross:
            cross_runtime = acknowledge_release_authority_handoff_plan(
                base.get("authorization_token", ""), confirm=HANDOFF_ACK_CONFIRMATION, operator_tab_id="tab-ack", operation_revision=41, runtime_root=Path(cross)
            )
        rows += [
            check("truthy-confirmation-rejected", not wrong.get("ok")),
            check("malformed-token-rejected", not malformed.get("ok")),
            check("cross-tab-token-rejected", not cross_tab.get("ok")),
            check("stale-revision-token-rejected", not stale_revision.get("ok")),
            check("cross-runtime-token-rejected", not cross_runtime.get("ok")),
        ]

        drift_fields = {
            "plan_id": "wrong-plan",
            "readiness_generation": 999999,
            "candidate_id": "wrong-candidate",
            "target_project_id": "wrong-project",
            "installation_transaction_id": "wrong-installation",
            "promotion_transaction_id": "wrong-promotion",
            "certification_transaction_id": "wrong-certification",
            "policy_sha256": "0" * 64,
            "migration_preview_sha256": "1" * 64,
            "archive_sha256": "2" * 64,
            "history_sha256": "3" * 64,
        }
        for index, (field, value) in enumerate(drift_fields.items(), start=50):
            preview = preview_release_authority_handoff_acknowledgment(
                operator_tab_id="tab-ack", operation_revision=index, runtime_root=runtime_root
            )
            rewritten = rewrite_token(runtime_root, preview["authorization_token"], field, value)
            result = acknowledge_release_authority_handoff_plan(
                rewritten, confirm=HANDOFF_ACK_CONFIRMATION, operator_tab_id="tab-ack", operation_revision=index, runtime_root=runtime_root
            )
            rows.append(check(f"{field}-token-rejected", not result.get("ok") and result.get("status") == "release_authority_handoff_authorization_stale"))

        expiring = preview_release_authority_handoff_acknowledgment(
            operator_tab_id="tab-expire", operation_revision=70, authorization_ttl_seconds=1, runtime_root=runtime_root
        )
        time.sleep(1.05)
        expired_auth = acknowledge_release_authority_handoff_plan(
            expiring["authorization_token"], confirm=HANDOFF_ACK_CONFIRMATION, operator_tab_id="tab-expire", operation_revision=70, runtime_root=runtime_root
        )
        rows.append(check("authorization-expiry-explicit", not expired_auth.get("ok") and expired_auth.get("status") == "release_authority_handoff_authorization_expired"))

        interrupted_preview = preview_release_authority_handoff_acknowledgment(
            operator_tab_id="tab-recover", operation_revision=80, acknowledgment_ttl_seconds=3600, runtime_root=runtime_root
        )
        interrupted = acknowledge_release_authority_handoff_plan(
            interrupted_preview["authorization_token"], confirm=HANDOFF_ACK_CONFIRMATION,
            operator_tab_id="tab-recover", operation_revision=80, interrupt_after="receipt_written", runtime_root=runtime_root
        )
        recovery_status = handoff_acknowledgment_recovery_status(runtime_root=runtime_root)
        wrong_recovery_owner = preview_handoff_acknowledgment_recovery(
            operator_tab_id="tab-wrong", operation_revision=80, runtime_root=runtime_root
        )
        recovery_preview = preview_handoff_acknowledgment_recovery(
            operator_tab_id="tab-recover", operation_revision=80, runtime_root=runtime_root
        )
        recovered = recover_handoff_acknowledgment(
            recovery_preview.get("authorization_token", ""), confirm=RECOVERY_CONFIRMATION,
            operator_tab_id="tab-recover", operation_revision=80, runtime_root=runtime_root
        )
        recovery_reused = recover_handoff_acknowledgment(
            recovery_preview.get("authorization_token", ""), confirm=RECOVERY_CONFIRMATION,
            operator_tab_id="tab-recover", operation_revision=80, runtime_root=runtime_root
        )
        ack_status = release_authority_handoff_acknowledgment_status(runtime_root=runtime_root)
        rows += [
            check("interrupted-ack-detected", not interrupted.get("ok") and interrupted.get("acknowledgment_operation_status") == "receipt_written"),
            check("exact-recovery-available", recovery_status.get("recovery_available")),
            check("cross-tab-recovery-rejected", not wrong_recovery_owner.get("ok")),
            check("recovery-preview-exact", recovery_preview.get("ok") and recovery_preview.get("literal_confirmation_required") == RECOVERY_CONFIRMATION),
            check("interrupted-ack-recovered", recovered.get("ok") and recovered.get("acknowledgment_recovery_performed")),
            check("recovery-token-single-use", not recovery_reused.get("ok")),
            check("completed-ack-current", ack_status.get("ok") and ack_status.get("acknowledgment_present")),
        ]

        old_ack_id, old_pointer_bytes = expire_active_ack(runtime_root)
        expired_status = release_authority_handoff_acknowledgment_status(runtime_root=runtime_root)
        replacement_status = handoff_acknowledgment_recovery_status(runtime_root=runtime_root)
        replacement_preview = preview_handoff_acknowledgment_replacement(
            operator_tab_id="tab-replace", operation_revision=90, acknowledgment_ttl_seconds=3600, runtime_root=runtime_root
        )
        interrupted_replacement = replace_handoff_acknowledgment(
            replacement_preview.get("authorization_token", ""), confirm=REPLACEMENT_CONFIRMATION,
            operator_tab_id="tab-replace", operation_revision=90, interrupt_after="receipt_written", runtime_root=runtime_root
        )
        pointer_after_failed_replacement = (handoff_plan_directory(runtime_root) / "active_acknowledgment.json").read_bytes()
        replacement_recovery = preview_handoff_acknowledgment_recovery(
            operator_tab_id="tab-replace", operation_revision=90, runtime_root=runtime_root
        )
        replaced = recover_handoff_acknowledgment(
            replacement_recovery.get("authorization_token", ""), confirm=RECOVERY_CONFIRMATION,
            operator_tab_id="tab-replace", operation_revision=90, runtime_root=runtime_root
        )
        current_after_replace = release_authority_handoff_acknowledgment_status(runtime_root=runtime_root)
        rows += [
            check("completed-ack-expiry-detected", expired_status.get("acknowledgment_expired") and not expired_status.get("ok")),
            check("expiry-does-not-auto-recreate", replacement_status.get("replacement_available") and not replacement_status.get("automatic_recreation_performed")),
            check("replacement-preview-exact", replacement_preview.get("ok") and replacement_preview.get("literal_confirmation_required") == REPLACEMENT_CONFIRMATION),
            check("replacement-interruption-detected", not interrupted_replacement.get("ok")),
            check("failed-replacement-preserves-old-pointer", pointer_after_failed_replacement != b"" and old_ack_id in pointer_after_failed_replacement.decode("utf-8")),
            check("replacement-recovery-preview", replacement_recovery.get("ok")),
            check("replacement-recovered", replaced.get("ok") and replaced.get("acknowledgment_id") != old_ack_id),
            check("replacement-current-nonreplayable", current_after_replace.get("ok") and not current_after_replace.get("acknowledgment_expired")),
        ]

        malformed_pointer = handoff_plan_directory(runtime_root) / "active_acknowledgment.json"
        pointer_backup = malformed_pointer.read_bytes()
        malformed_pointer.write_text("{", encoding="utf-8")
        malformed_status = release_authority_handoff_acknowledgment_status(runtime_root=runtime_root)
        malformed_pointer.write_bytes(pointer_backup)
        orphan = handoff_plan_directory(runtime_root) / "acknowledgments" / "orphan-malformed.json"
        orphan.parent.mkdir(parents=True, exist_ok=True)
        orphan.write_text("{", encoding="utf-8")
        cleanup_preview = preview_handoff_acknowledgment_cleanup(runtime_root=runtime_root)
        wrong_cleanup = cleanup_handoff_acknowledgment_artifacts(
            cleanup_preview.get("authorization_token", ""), confirm="cleanup", runtime_root=runtime_root
        )
        cleaned = cleanup_handoff_acknowledgment_artifacts(
            cleanup_preview.get("authorization_token", ""), confirm=CLEANUP_CONFIRMATION, runtime_root=runtime_root
        )
        rows += [
            check("malformed-active-pointer-detected", not malformed_status.get("ok")),
            check("cleanup-preview-exact", cleanup_preview.get("ok") and cleanup_preview.get("cleanup_artifact_count", 0) >= 1),
            check("cleanup-truthy-rejected", not wrong_cleanup.get("ok")),
            check("exact-abandoned-cleanup", cleaned.get("ok") and not orphan.exists()),
        ]

        old_env = os.environ.get("EIDOLON_DATA_DIR")
        os.environ["EIDOLON_DATA_DIR"] = str(runtime_root)
        get_code, get_payload = handle_api_get("/api/release-authority/handoff-plan/acknowledgment/status")
        recovery_code, recovery_payload = handle_api_get("/api/release-authority/handoff-plan/acknowledgment/recovery/status")
        post_code, post_payload = handle_api_post("/api/release-authority/handoff-plan/acknowledgment/recovery-preview", {"operator_tab_id": "tab-replace", "operation_revision": 90})
        try:
            handle_api_get("/api/release-authority/handoff-plan/acknowledgment/recover")
            post_only = False
        except ApiError as exc:
            post_only = exc.status == 404
        if old_env is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old_env
        rows += [
            check("ack-status-get", get_code == 200 and "data" in get_payload),
            check("ack-recovery-status-get", recovery_code == 200 and "data" in recovery_payload),
            check("ack-recovery-preview-post", post_code in {200, 409} and "data" in post_payload),
            check("ack-mutations-post-only", post_only),
        ]

        public = json.dumps({"ack": current_after_replace, "recovery": handoff_acknowledgment_recovery_status(runtime_root=runtime_root)}, sort_keys=True)
        rows += [
            check("ack-paths-suppressed", str(runtime_root) not in public and str(target) not in public and "/tmp/" not in public),
            check("target-unchanged", file_snapshot(target) == target_before),
            check("no-provider-native-model-actions", not current_after_replace.get("provider_contacted") and not current_after_replace.get("native_checks_run") and not current_after_replace.get("models_mutated")),
            check("no-install-promotion-certification-actions", not current_after_replace.get("installation_changed") and not current_after_replace.get("promotion_changed") and not current_after_replace.get("certification_changed") and not current_after_replace.get("policy_migrated")),
        ]

    report = {
        "suite": "v1098.4-handoff-acknowledgment-recovery-expiry-hardening",
        "passed": sum(bool(row["ok"]) for row in rows),
        "failed": sum(not bool(row["ok"]) for row in rows),
        "checks": rows,
    }
    report["ok"] = report["failed"] == 0
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
