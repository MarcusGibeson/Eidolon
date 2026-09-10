from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
for item in (ROOT / "conscious_agent", ROOT / "tools"):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from v1098_bundle_a_test_support import file_snapshot, prepare_ready_fixture
from release_authority_readiness_recovery import refresh_release_authority_readiness
from release_authority_handoff_plan import (
    HANDOFF_ACK_CONFIRMATION,
    acknowledge_release_authority_handoff_plan,
    create_release_authority_handoff_plan,
    handoff_plan_directory,
    preview_release_authority_handoff_acknowledgment,
    release_authority_handoff_acknowledgment_status,
    release_authority_handoff_plan_status,
)
from api_server import ApiError, handle_api_get, handle_api_post


def check(name: str, ok: object) -> dict[str, object]:
    return {"name": name, "ok": bool(ok)}


def main() -> int:
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="eidolon-v1098-2-") as temp:
        fixture = prepare_ready_fixture(Path(temp))
        runtime_root = Path(fixture["runtime_root"])
        target = Path(fixture["target"])
        target_before = file_snapshot(target)
        refresh_release_authority_readiness(runtime_root=runtime_root)
        plan = create_release_authority_handoff_plan(runtime_root=runtime_root)
        status = release_authority_handoff_plan_status(runtime_root=runtime_root)
        required = (
            "readiness_binding_sha256", "candidate_id", "source_manifest_sha256", "archive_manifest_sha256", "archive_sha256",
            "installation_transaction_id", "installed_receipt_sha256", "target_project_id", "target_inventory_sha256",
            "promotion_transaction_id", "promotion_receipt_sha256", "certification_receipt_sha256", "history_sha256", "policy_sha256", "migration_preview_sha256",
        )
        scopes = {row.get("scope"): row for row in status.get("scope_statuses") or []}
        rows += [
            check("handoff-plan-created", plan.get("ok") and plan.get("status") == "release_authority_handoff_plan_bound"),
            check("handoff-plan-current", status.get("ok") and status.get("status") == "release_authority_handoff_plan_current"),
            check("exact-plan-bindings", all(status.get(field) for field in required)),
            check("scope-rows-content-free", set(scopes) == {"general_release", "native_windows", "provider_ollama", "model_specific"} and all(row.get("content_free") for row in scopes.values())),
            check("scope-authority-separated", scopes["general_release"].get("certified") and not scopes["native_windows"].get("certified") and not scopes["provider_ollama"].get("certified")),
            check("unresolved-blockers-bounded", status.get("unresolved_blocker_count") == 0),
        ]

        auth_preview = preview_release_authority_handoff_acknowledgment(runtime_root=runtime_root)
        wrong = acknowledge_release_authority_handoff_plan(auth_preview.get("authorization_token", ""), confirm="ack", runtime_root=runtime_root)
        with tempfile.TemporaryDirectory(prefix="eidolon-v1098-2-cross-") as cross:
            cross_result = acknowledge_release_authority_handoff_plan(auth_preview.get("authorization_token", ""), confirm=HANDOFF_ACK_CONFIRMATION, runtime_root=Path(cross))
        acknowledged = acknowledge_release_authority_handoff_plan(auth_preview.get("authorization_token", ""), confirm=HANDOFF_ACK_CONFIRMATION, runtime_root=runtime_root)
        reused = acknowledge_release_authority_handoff_plan(auth_preview.get("authorization_token", ""), confirm=HANDOFF_ACK_CONFIRMATION, runtime_root=runtime_root)
        ack_status = release_authority_handoff_acknowledgment_status(runtime_root=runtime_root)
        rows += [
            check("acknowledgment-preview-exact", auth_preview.get("ok") and auth_preview.get("literal_confirmation_required") == HANDOFF_ACK_CONFIRMATION),
            check("acknowledgment-truthy-rejected", not wrong.get("ok")),
            check("acknowledgment-cross-runtime-rejected", not cross_result.get("ok")),
            check("handoff-plan-acknowledged", acknowledged.get("ok") and not acknowledged.get("acknowledgment_grants_authority")),
            check("acknowledgment-token-burned", not reused.get("ok") and reused.get("status") == "authorization_reused"),
            check("acknowledgment-current", ack_status.get("ok") and ack_status.get("acknowledgment_present")),
        ]

        old_plan_id = status["plan_id"]
        refresh_release_authority_readiness(runtime_root=runtime_root)
        stale = release_authority_handoff_plan_status(runtime_root=runtime_root)
        stale_ack = release_authority_handoff_acknowledgment_status(runtime_root=runtime_root)
        rows += [
            check("plan-drift-detected", not stale.get("ok") and stale.get("status") == "release_authority_handoff_plan_stale"),
            check("acknowledgment-drift-detected", not stale_ack.get("ok")),
        ]

        new_plan = create_release_authority_handoff_plan(runtime_root=runtime_root)
        stale_auth = preview_release_authority_handoff_acknowledgment(runtime_root=runtime_root)
        refresh_release_authority_readiness(runtime_root=runtime_root)
        stale_apply = acknowledge_release_authority_handoff_plan(stale_auth.get("authorization_token", ""), confirm=HANDOFF_ACK_CONFIRMATION, runtime_root=runtime_root)
        rows += [
            check("replanning-after-refresh", new_plan.get("ok") and new_plan.get("plan_id") != old_plan_id),
            check("stale-plan-token-rejected", not stale_apply.get("ok") and stale_apply.get("status") == "release_authority_handoff_authorization_stale"),
        ]

        pointer_path = handoff_plan_directory(runtime_root) / "active_plan.json"
        preserved_pointer = pointer_path.read_bytes()
        readiness_pointer = Path(runtime_root) / "release_authority_readiness" / "active_readiness.json"
        readiness_backup = readiness_pointer.read_bytes()
        readiness_pointer.write_text("{", encoding="utf-8")
        failed_replan = create_release_authority_handoff_plan(runtime_root=runtime_root)
        rows += [
            check("failed-replan-preserves-active-plan", not failed_replan.get("ok") and pointer_path.read_bytes() == preserved_pointer),
        ]
        readiness_pointer.write_bytes(readiness_backup)

        old_env = os.environ.get("EIDOLON_DATA_DIR")
        os.environ["EIDOLON_DATA_DIR"] = str(runtime_root)
        get_code, get_payload = handle_api_get("/api/release-authority/handoff-plan/status")
        post_code, post_payload = handle_api_post("/api/release-authority/handoff-plan/create", {})
        try:
            handle_api_get("/api/release-authority/handoff-plan/create")
            post_only = False
        except ApiError as exc:
            post_only = exc.status == 404
        if old_env is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old_env
        rows += [
            check("handoff-plan-status-get", get_code == 200 and "data" in get_payload),
            check("handoff-plan-create-post", post_code in {200, 409} and "data" in post_payload),
            check("handoff-plan-create-get-blocked", post_only),
        ]

        public = json.dumps(release_authority_handoff_plan_status(runtime_root=runtime_root), sort_keys=True)
        rows += [
            check("handoff-paths-suppressed", str(runtime_root) not in public and str(target) not in public and "/tmp/" not in public),
            check("target-remains-unchanged", file_snapshot(target) == target_before),
            check("no-authority-action", not plan.get("installation_changed") and not plan.get("promotion_changed") and not plan.get("certification_changed") and not plan.get("policy_migrated")),
        ]

    report = {
        "suite": "v1098.2-release-authority-handoff-plan-binding",
        "passed": sum(bool(row["ok"]) for row in rows),
        "failed": sum(not bool(row["ok"]) for row in rows),
        "checks": rows,
    }
    report["ok"] = report["failed"] == 0
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
