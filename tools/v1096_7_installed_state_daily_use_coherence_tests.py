from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))

from release_installed_state import installed_state_status
from api_server import ApiError, handle_api_get, handle_api_post
from release_installation_recovery import (
    ROLLBACK_CONFIRMATION,
    preview_installation_rollback,
    rollback_installation_transaction,
)
from release_installation_transaction import (
    INSTALLATION_APPLY_CONFIRMATION,
    apply_authorized_installation,
    preview_installation_apply_authorization,
)
from v1096_bundle_c_test_support import prepare_staged_fixture


def check(name: str, ok: object, detail: str = "") -> dict[str, object]:
    return {"name": name, "ok": bool(ok), "detail": detail}


def apply(fixture: dict, interrupt: str = "") -> dict:
    runtime = fixture["handoff_runtime"]
    auth = preview_installation_apply_authorization(runtime_root=runtime)
    return apply_authorized_installation(
        str(auth.get("authorization_token") or ""), confirm=INSTALLATION_APPLY_CONFIRMATION,
        runtime_root=runtime, _interrupt_at=interrupt,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    rows: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-7-staged-") as td:
        fixture = prepare_staged_fixture(Path(td))
        status = installed_state_status(runtime_root=fixture["handoff_runtime"])
        rows.append(check("stage-alone-not-installation", status.get("ok") and status.get("status") in {"staged", "not_staged"} and not status.get("installed")))
        rows.append(check("no-source-similarity-inference", not status.get("installation_inferred_from_source_similarity") and not status.get("installation_inferred_from_archive_filename") and not status.get("installation_inferred_from_candidate_or_staging_record")))

    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-7-interrupted-") as td:
        fixture = prepare_staged_fixture(Path(td))
        apply(fixture, "after_backup")
        status = installed_state_status(runtime_root=fixture["handoff_runtime"])
        rows.append(check("interrupted-state-distinct", status.get("status") == "interrupted" and status.get("interrupted") and not status.get("installed")))

    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-7-rollback-ready-") as td:
        fixture = prepare_staged_fixture(Path(td))
        apply(fixture, "after_effect:1")
        status = installed_state_status(runtime_root=fixture["handoff_runtime"])
        rows.append(check("rollback-ready-state-distinct", status.get("ok") and status.get("status") == "rollback_ready" and status.get("rollback_ready")))

    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-7-installed-") as td:
        fixture = prepare_staged_fixture(Path(td))
        applied = apply(fixture)
        runtime = fixture["handoff_runtime"]
        status = installed_state_status(runtime_root=runtime)
        rows.append(check("installed-unpromoted-reconciled", applied.get("ok") and status.get("ok") and status.get("status") == "installed_unpromoted" and status.get("installed_receipt_valid")))
        rows.append(check("candidate-transaction-receipt-bound", status.get("candidate_id") == applied.get("candidate_id") and status.get("archive_sha256") == applied.get("archive_sha256") and status.get("transaction_identity_sha256")))
        rows.append(check("promotion-certification-authority-separate", not status.get("promoted") and not status.get("certified") and not status.get("certification_actions_available")))
        public = json.dumps(status, sort_keys=True)
        rows.append(check("installed-status-path-suppressed", str(fixture["target"]) not in public and str(fixture["archive"]) not in public and status.get("paths_suppressed") and status.get("content_free")))
        rows.append(check("ordinary-conversation-unaffected", not status.get("ordinary_conversation_affected") and not status.get("provider_contacted")))
        previous_data_dir = os.environ.get("EIDOLON_DATA_DIR")
        os.environ["EIDOLON_DATA_DIR"] = str(runtime)
        try:
            code, api_payload = handle_api_get("/api/release-installation/installed-state/status")
            rows.append(check("standalone-api-read-only-status", code == 200 and api_payload.get("data", {}).get("status") == "installed_unpromoted"))
            try:
                handle_api_get("/api/release-installation/transaction/apply")
                get_mutation_rejected = False
            except ApiError as error:
                get_mutation_rejected = error.status == 404
            rows.append(check("mutations-not-registered-as-get", get_mutation_rejected))
            post_code, post_payload = handle_api_post("/api/release-installation/transaction/apply", {"authorization_token": "bad", "confirm": "true"})
            rows.append(check("mutation-post-only-and-confirmed", post_code == 409 and not post_payload.get("data", {}).get("ok")))
        finally:
            if previous_data_dir is None:
                os.environ.pop("EIDOLON_DATA_DIR", None)
            else:
                os.environ["EIDOLON_DATA_DIR"] = previous_data_dir
        (fixture["target"] / "README.md").write_text("external drift after completed installation\n", encoding="utf-8")
        drift = installed_state_status(runtime_root=runtime)
        rows.append(check("installed-target-drift-uncertain", not drift.get("ok") and drift.get("status") == "uncertain" and not drift.get("installed")))

    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-7-rolledback-") as td:
        fixture = prepare_staged_fixture(Path(td))
        apply(fixture)
        runtime = fixture["handoff_runtime"]
        preview = preview_installation_rollback(runtime_root=runtime)
        rolled = rollback_installation_transaction(str(preview.get("authorization_token") or ""), confirm=ROLLBACK_CONFIRMATION, runtime_root=runtime)
        status = installed_state_status(runtime_root=runtime)
        rows.append(check("rolled-back-state-distinct", rolled.get("ok") and status.get("ok") and status.get("status") == "rolled_back" and status.get("rolled_back") and not status.get("installed")))
        rows.append(check("rolled-back-authority-separate", not status.get("promoted") and not status.get("certified")))

    # A source-like target without an exact transaction receipt is never installed.
    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-7-similarity-") as td:
        fixture = prepare_staged_fixture(Path(td))
        target = fixture["target"]
        source = fixture["source"]
        (target / "README.md").write_bytes((source / "README.md").read_bytes())
        (target / fixture["add_relative"]).write_bytes((source / fixture["add_relative"]).read_bytes())
        (target / fixture["remove_relative"]).unlink()
        status = installed_state_status(runtime_root=fixture["handoff_runtime"])
        rows.append(check("similarity-without-transaction-not-installed", status.get("status") in {"staged", "not_staged"} and not status.get("installed")))

    dashboard_text = (ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
    rows.append(check("dashboard-bounded-status-surfaces", all(token in dashboard_text for token in (
        "/api/release-installation/transaction/status", "/api/release-installation/recovery/status", "/api/release-installation/installed-state/status",
        "/api/release-installation/transaction/apply", "/api/release-installation/recovery/rollback",
    ))))
    rows.append(check("dashboard-parses-post-body-before-installation-actions", dashboard_text.index("body = parse_request_body(raw_body") < dashboard_text.index("/api/release-installation/transaction/apply")))

    report = {
        "suite": "v1096.7-installed-state-reconciliation-daily-use-coherence",
        "passed": sum(bool(row["ok"]) for row in rows),
        "failed": sum(not bool(row["ok"]) for row in rows),
        "checks": rows,
    }
    report["ok"] = report["failed"] == 0
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
