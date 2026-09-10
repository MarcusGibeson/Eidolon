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
    preview_release_authority_handoff_acknowledgment,
)
from release_authority_daily_use import release_authority_daily_use_status
from release_certification_coherence import (
    OPERATION_CLAIM_CONFIRMATION,
    OPERATION_RELEASE_CONFIRMATION,
    claim_operation,
    preview_operation_claim,
    release_operation,
)
from api_server import ApiError, handle_api_get
from dashboard import render_release_certification


def check(name: str, ok: object) -> dict[str, object]:
    return {"name": name, "ok": bool(ok)}


def main() -> int:
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="eidolon-v1098-3-") as temp:
        fixture = prepare_ready_fixture(Path(temp))
        runtime_root = Path(fixture["runtime_root"])
        target = Path(fixture["target"])
        target_before = file_snapshot(target)
        refresh_release_authority_readiness(runtime_root=runtime_root)
        create_release_authority_handoff_plan(runtime_root=runtime_root)
        auth = preview_release_authority_handoff_acknowledgment(runtime_root=runtime_root)
        acknowledge_release_authority_handoff_plan(auth.get("authorization_token", ""), confirm=HANDOFF_ACK_CONFIRMATION, runtime_root=runtime_root)
        status = release_authority_daily_use_status(runtime_root=runtime_root)
        status_again = release_authority_daily_use_status(runtime_root=runtime_root)
        rows += [
            check("daily-use-coherent", status.get("ok") and status.get("status") == "release_authority_daily_use_coherent"),
            check("readiness-refresh-consolidated", status.get("readiness_generation") and status.get("refresh_generation")),
            check("handoff-consolidated", status.get("handoff_plan_id") and status.get("handoff_acknowledged")),
            check("authority-history-policy-consolidated", status.get("authority_status") and status.get("history_status") and status.get("policy_status") and status.get("migration_status")),
            check("restart-stable-status", status == status_again),
            check("scope-authority-exact", status.get("certified_scopes") == ["general_release"]),
            check("no-unresolved-blockers", status.get("unresolved_blocker_count") == 0),
        ]

        claim_preview = preview_operation_claim("release_authority_readiness_refresh", "tab-a", 31, runtime_root=runtime_root)
        claimed = claim_operation(claim_preview.get("authorization_token", ""), confirm=OPERATION_CLAIM_CONFIRMATION, runtime_root=runtime_root)
        other_tab = preview_operation_claim("release_authority_handoff_plan", "tab-b", 32, runtime_root=runtime_root)
        stale_revision = preview_operation_claim("release_authority_readiness_recovery", "tab-a", 30, runtime_root=runtime_root)
        owner_status = release_authority_daily_use_status(runtime_root=runtime_root)
        released = release_operation("tab-a", claimed.get("operation_generation", 0), confirm=OPERATION_RELEASE_CONFIRMATION, runtime_root=runtime_root)
        after_release = release_authority_daily_use_status(runtime_root=runtime_root)
        rows += [
            check("refresh-operation-claim", claim_preview.get("ok") and claimed.get("ok")),
            check("other-tab-blocked", not other_tab.get("ok") and other_tab.get("status") == "operation_owned_by_other_tab"),
            check("stale-revision-blocked", not stale_revision.get("ok")),
            check("owner-visible-bounded", owner_status.get("operation_owner_present") and owner_status.get("operation") == "release_authority_readiness_refresh"),
            check("owner-release-exact", released.get("ok") and not after_release.get("operation_owner_present")),
        ]

        refresh_release_authority_readiness(runtime_root=runtime_root)
        drifted = release_authority_daily_use_status(runtime_root=runtime_root)
        rows += [
            check("handoff-plan-drift-surfaces", not drifted.get("ok") and drifted.get("status") == "release_authority_daily_use_attention_required"),
            check("no-authority-transfer-on-refresh", not drifted.get("authority_transfer_on_refresh") and drifted.get("certified_scopes") == ["general_release"]),
        ]

        old_env = os.environ.get("EIDOLON_DATA_DIR")
        os.environ["EIDOLON_DATA_DIR"] = str(runtime_root)
        code, payload = handle_api_get("/api/release-authority/daily-use/status")
        try:
            handle_api_get("/api/release-authority/handoff-plan/acknowledge")
            mutation_get_blocked = False
        except ApiError as exc:
            mutation_get_blocked = exc.status == 404
        html = render_release_certification()
        if old_env is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old_env
        rows += [
            check("daily-use-api-get", code == 200 and payload.get("data", {}).get("status") in {"release_authority_daily_use_coherent", "release_authority_daily_use_attention_required"}),
            check("mutations-remain-post-only", mutation_get_blocked),
            check("dashboard-bounded-status", "Release authority daily use" in html and "Authority handoff plan" in html and "Readiness refresh" in html),
            check("dashboard-path-suppressed", str(runtime_root) not in html and str(target) not in html),
        ]

        public = json.dumps(drifted, sort_keys=True)
        rows += [
            check("ordinary-conversation-unaffected", drifted.get("ordinary_conversation_affected") is False),
            check("no-install-promotion-certification-inference", not drifted.get("installation_inferred") and not drifted.get("promotion_inferred") and not drifted.get("general_release_certification_inferred") and not drifted.get("native_windows_inferred") and not drifted.get("provider_ollama_inferred") and not drifted.get("model_specific_inferred")),
            check("public-paths-suppressed", str(runtime_root) not in public and str(target) not in public and "/tmp/" not in public),
            check("no-provider-or-native-actions", not drifted.get("provider_contacted") and not drifted.get("native_checks_run") and not drifted.get("models_mutated")),
            check("target-unchanged", file_snapshot(target) == target_before),
        ]

    report = {
        "suite": "v1098.3-release-authority-daily-use-coherence-checkpoint",
        "passed": sum(bool(row["ok"]) for row in rows),
        "failed": sum(not bool(row["ok"]) for row in rows),
        "checks": rows,
    }
    report["ok"] = report["failed"] == 0
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
