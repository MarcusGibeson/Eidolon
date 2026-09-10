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
from release_authority_readiness import release_authority_readiness_directory, release_authority_readiness_status
from release_authority_readiness_recovery import (
    CLEANUP_CONFIRMATION,
    REFRESH_RECOVERY_CONFIRMATION,
    REPLACEMENT_CONFIRMATION,
    cleanup_readiness_artifacts,
    preview_readiness_cleanup,
    preview_readiness_refresh_recovery,
    preview_readiness_snapshot_replacement,
    readiness_refresh_status,
    refresh_release_authority_readiness,
    replace_release_authority_readiness_snapshot,
    resume_release_authority_readiness_refresh,
)
from api_server import ApiError, handle_api_get, handle_api_post


def check(name: str, ok: object) -> dict[str, object]:
    return {"name": name, "ok": bool(ok)}


def main() -> int:
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="eidolon-v1098-1-") as temp:
        base = Path(temp)
        fixture = prepare_ready_fixture(base)
        runtime_root = Path(fixture["runtime_root"])
        target = Path(fixture["target"])
        target_before = file_snapshot(target)
        initial = release_authority_readiness_status(runtime_root=runtime_root)
        initial_id = initial["preview_id"]
        initial_generation = initial["generation"]

        interrupted = refresh_release_authority_readiness(runtime_root=runtime_root, interrupt_after="before_activation")
        active_after_interrupt = release_authority_readiness_status(runtime_root=runtime_root)
        rows += [
            check("refresh-interruption-recorded", interrupted.get("status") == "readiness_refresh_interrupted" and interrupted.get("recovery_available")),
            check("previous-snapshot-preserved", active_after_interrupt.get("preview_id") == initial_id and active_after_interrupt.get("generation") == initial_generation),
            check("refresh-generation-exact", interrupted.get("proposed_generation") == initial_generation + 1),
        ]
        recovery_preview = preview_readiness_refresh_recovery(runtime_root=runtime_root)
        wrong = resume_release_authority_readiness_refresh(recovery_preview.get("authorization_token", ""), confirm="yes", runtime_root=runtime_root)
        with tempfile.TemporaryDirectory(prefix="eidolon-v1098-1-cross-") as cross:
            cross_result = resume_release_authority_readiness_refresh(recovery_preview.get("authorization_token", ""), confirm=REFRESH_RECOVERY_CONFIRMATION, runtime_root=Path(cross))
        resumed = resume_release_authority_readiness_refresh(recovery_preview.get("authorization_token", ""), confirm=REFRESH_RECOVERY_CONFIRMATION, runtime_root=runtime_root)
        reused = resume_release_authority_readiness_refresh(recovery_preview.get("authorization_token", ""), confirm=REFRESH_RECOVERY_CONFIRMATION, runtime_root=runtime_root)
        rows += [
            check("recovery-preview-exact", recovery_preview.get("ok") and recovery_preview.get("literal_confirmation_required") == REFRESH_RECOVERY_CONFIRMATION),
            check("truthy-confirmation-rejected", not wrong.get("ok") and wrong.get("status") == "literal_confirmation_required"),
            check("cross-runtime-token-rejected", not cross_result.get("ok")),
            check("interrupted-refresh-recovered", resumed.get("ok") and resumed.get("active_generation") == initial_generation + 1),
            check("recovery-token-burned", not reused.get("ok") and reused.get("status") == "authorization_reused"),
        ]

        refreshed = refresh_release_authority_readiness(runtime_root=runtime_root)
        rows += [
            check("normal-refresh-complete", refreshed.get("ok") and refreshed.get("status") == "release_authority_readiness_refreshed"),
            check("refresh-generation-monotonic", refreshed.get("active_generation") == initial_generation + 2),
            check("refresh-status-current", readiness_refresh_status(runtime_root=runtime_root).get("ok")),
        ]

        replacement_preview = preview_readiness_snapshot_replacement(initial_id, runtime_root=runtime_root)
        wrong_replace = replace_release_authority_readiness_snapshot(replacement_preview.get("authorization_token", ""), confirm="true", runtime_root=runtime_root)
        replaced = replace_release_authority_readiness_snapshot(replacement_preview.get("authorization_token", ""), confirm=REPLACEMENT_CONFIRMATION, runtime_root=runtime_root)
        replacement_reuse = replace_release_authority_readiness_snapshot(replacement_preview.get("authorization_token", ""), confirm=REPLACEMENT_CONFIRMATION, runtime_root=runtime_root)
        rows += [
            check("replacement-preview-first", replacement_preview.get("ok") and replacement_preview.get("replacement_available")),
            check("replacement-literal-required", not wrong_replace.get("ok")),
            check("snapshot-replaced-with-new-generation", replaced.get("ok") and replaced.get("active_generation") == initial_generation + 3),
            check("replacement-token-burned", not replacement_reuse.get("ok") and replacement_reuse.get("status") == "authorization_reused"),
        ]

        temporary = release_authority_readiness_directory(runtime_root) / "temporary"
        (temporary / "nested").mkdir(parents=True, exist_ok=True)
        (temporary / "one.tmp").write_text("one", encoding="utf-8")
        (temporary / "nested" / "two.tmp").write_text("two", encoding="utf-8")
        cleanup_preview = preview_readiness_cleanup(runtime_root=runtime_root)
        wrong_cleanup = cleanup_readiness_artifacts(cleanup_preview.get("authorization_token", ""), confirm="remove", runtime_root=runtime_root)
        cleaned = cleanup_readiness_artifacts(cleanup_preview.get("authorization_token", ""), confirm=CLEANUP_CONFIRMATION, runtime_root=runtime_root)
        cleanup_reuse = cleanup_readiness_artifacts(cleanup_preview.get("authorization_token", ""), confirm=CLEANUP_CONFIRMATION, runtime_root=runtime_root)
        rows += [
            check("cleanup-owned-artifacts-previewed", cleanup_preview.get("ok") and cleanup_preview.get("artifact_count") == 2),
            check("cleanup-literal-required", not wrong_cleanup.get("ok")),
            check("cleanup-exact-artifacts", cleaned.get("ok") and not any(temporary.rglob("*.tmp"))),
            check("cleanup-token-burned", not cleanup_reuse.get("ok")),
        ]

        old_env = os.environ.get("EIDOLON_DATA_DIR")
        os.environ["EIDOLON_DATA_DIR"] = str(runtime_root)
        get_code, get_payload = handle_api_get("/api/release-authority/readiness/refresh/status")
        post_code, post_payload = handle_api_post("/api/release-authority/readiness/refresh", {})
        try:
            handle_api_get("/api/release-authority/readiness/refresh")
            mutation_get_blocked = False
        except ApiError as exc:
            mutation_get_blocked = exc.status == 404
        if old_env is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old_env
        rows += [
            check("refresh-status-get", get_code == 200 and "data" in get_payload),
            check("refresh-mutation-post", post_code == 200 and post_payload.get("data", {}).get("ok")),
            check("refresh-mutation-get-blocked", mutation_get_blocked),
        ]

        public = json.dumps(readiness_refresh_status(runtime_root=runtime_root), sort_keys=True)
        rows += [
            check("paths-suppressed", str(runtime_root) not in public and str(target) not in public and "/tmp/" not in public),
            check("no-native-or-provider-rerun", readiness_refresh_status(runtime_root=runtime_root).get("native_checks_run") is False and readiness_refresh_status(runtime_root=runtime_root).get("provider_contacted") is False),
            check("target-unchanged", file_snapshot(target) == target_before),
        ]

        pointer_path = release_authority_readiness_directory(runtime_root) / "active_readiness.json"
        pointer_backup = pointer_path.read_bytes()
        pointer_path.write_text("{", encoding="utf-8")
        blocked = refresh_release_authority_readiness(runtime_root=runtime_root)
        rows.append(check("malformed-pointer-detected", not blocked.get("ok") and blocked.get("status") == "coherent_active_readiness_required"))
        pointer_path.write_bytes(pointer_backup)

    report = {
        "suite": "v1098.1-release-authority-readiness-refresh-recovery-hardening",
        "passed": sum(bool(row["ok"]) for row in rows),
        "failed": sum(not bool(row["ok"]) for row in rows),
        "checks": rows,
    }
    report["ok"] = report["failed"] == 0
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
