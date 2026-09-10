from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))

from release_candidate_identity import read_json
from release_installation_recovery import (
    RESUME_CONFIRMATION,
    ROLLBACK_CONFIRMATION,
    inspect_installation_transaction,
    preview_installation_resume,
    preview_installation_rollback,
    resume_installation_transaction,
    rollback_installation_transaction,
)
from release_installation_transaction import (
    INSTALLATION_APPLY_CONFIRMATION,
    apply_authorized_installation,
    preview_installation_apply_authorization,
    transaction_directory,
)
from v1096_bundle_c_test_support import prepare_staged_fixture, snapshot_files


def check(name: str, ok: object, detail: str = "") -> dict[str, object]:
    return {"name": name, "ok": bool(ok), "detail": detail}


def begin_apply(fixture: dict, interrupt_at: str = "") -> dict:
    runtime = fixture["handoff_runtime"]
    auth = preview_installation_apply_authorization(runtime_root=runtime)
    return apply_authorized_installation(
        str(auth.get("authorization_token") or ""),
        confirm=INSTALLATION_APPLY_CONFIRMATION,
        runtime_root=runtime,
        _interrupt_at=interrupt_at,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    rows: list[dict[str, object]] = []


    # Interruption before backup creation can resume without target mutation.
    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-6-before-backup-") as td:
        fixture = prepare_staged_fixture(Path(td))
        before = dict(fixture["target_before"])
        interrupted = begin_apply(fixture, "before_backup")
        runtime = fixture["handoff_runtime"]
        rows.append(check("before-backup-interruption-detected", interrupted.get("status") == "interrupted" and interrupted.get("backup_count") == 0 and interrupted.get("completed_effect_count") == 0))
        rows.append(check("before-backup-target-unchanged", snapshot_files(fixture["target"]) == before))
        preview = preview_installation_resume(runtime_root=runtime)
        resumed = resume_installation_transaction(str(preview.get("authorization_token") or ""), confirm=RESUME_CONFIRMATION, runtime_root=runtime)
        rows.append(check("before-backup-resume-completes", resumed.get("ok") and resumed.get("status") == "installed_unpromoted"))

    # Corrupted verified backups fail closed before resume or rollback.
    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-6-backup-integrity-") as td:
        fixture = prepare_staged_fixture(Path(td))
        interrupted = begin_apply(fixture, "after_backup")
        runtime = fixture["handoff_runtime"]
        pointer = read_json(transaction_directory(runtime) / "active_transaction.json")
        record = read_json(transaction_directory(runtime) / "records" / f"{pointer.get('transaction_id','')}.json")
        completed_backups = list(record.get("backups_completed") or [])
        backup_path = Path(str(record.get("backup_root_path") or "")) / completed_backups[0]
        backup_path.write_bytes(b"corrupted backup bytes\n")
        status = inspect_installation_transaction(runtime_root=runtime)
        rows.append(check("backup-integrity-contradiction-detected", interrupted.get("status") == "interrupted" and not status.get("ok") and status.get("status") == "uncertain" and any(row.get("kind") == "backup_changed_or_missing" for row in status.get("findings", []))))
        rows.append(check("corrupt-backup-resume-blocked", not preview_installation_resume(runtime_root=runtime).get("ok")))
        rows.append(check("corrupt-backup-rollback-blocked", not preview_installation_rollback(runtime_root=runtime).get("ok")))

    # Interruption after backup completion can resume exactly.
    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-6-resume-") as td:
        fixture = prepare_staged_fixture(Path(td))
        interrupted = begin_apply(fixture, "after_backup")
        runtime = fixture["handoff_runtime"]
        rows.append(check("after-backup-interruption-detected", interrupted.get("status") == "interrupted" and interrupted.get("backup_count", 0) >= 2 and interrupted.get("completed_effect_count") == 0))
        status = inspect_installation_transaction(runtime_root=runtime)
        rows.append(check("resume-ready-exact-state", status.get("ok") and status.get("resume_available") and not status.get("owner_alive")))
        preview = preview_installation_resume(runtime_root=runtime)
        token = str(preview.get("authorization_token") or "")
        rows.append(check("resume-preview-bound", preview.get("ok") and token and preview.get("literal_confirmation") == RESUME_CONFIRMATION))
        bad = resume_installation_transaction(token, confirm="true", runtime_root=runtime)
        rows.append(check("resume-literal-required", not bad.get("ok")))
        resumed = resume_installation_transaction(token, confirm=RESUME_CONFIRMATION, runtime_root=runtime)
        rows.append(check("resume-completes-installation", resumed.get("ok") and resumed.get("status") == "installed_unpromoted"))
        reused = resume_installation_transaction(token, confirm=RESUME_CONFIRMATION, runtime_root=runtime)
        rows.append(check("resume-token-single-use", not reused.get("ok")))

    # Interruption after all mutations but before finalization can reconcile and finalize.
    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-6-finalize-") as td:
        fixture = prepare_staged_fixture(Path(td))
        interrupted = begin_apply(fixture, "after_mutation_before_finalize")
        runtime = fixture["handoff_runtime"]
        status = inspect_installation_transaction(runtime_root=runtime)
        rows.append(check("post-mutation-interruption-detected", interrupted.get("status") == "interrupted" and interrupted.get("completed_effect_count") == interrupted.get("total_effect_count")))
        rows.append(check("post-mutation-resume-available", status.get("ok") and status.get("resume_available") and status.get("rollback_available")))
        preview = preview_installation_resume(runtime_root=runtime)
        finalized = resume_installation_transaction(str(preview.get("authorization_token") or ""), confirm=RESUME_CONFIRMATION, runtime_root=runtime)
        rows.append(check("finalization-resumed-idempotently", finalized.get("ok") and finalized.get("status") == "installed_unpromoted"))

    # Partial rollback survives interruption and resumes idempotently.
    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-6-rollback-") as td:
        fixture = prepare_staged_fixture(Path(td))
        before = dict(fixture["target_before"])
        installed = begin_apply(fixture)
        runtime = fixture["handoff_runtime"]
        rows.append(check("rollback-fixture-installed", installed.get("ok")))
        preview = preview_installation_rollback(runtime_root=runtime)
        rows.append(check("rollback-preview-bound", preview.get("ok") and preview.get("literal_confirmation") == ROLLBACK_CONFIRMATION))
        partial = rollback_installation_transaction(
            str(preview.get("authorization_token") or ""),
            confirm=ROLLBACK_CONFIRMATION,
            runtime_root=runtime,
            _interrupt_after=1,
        )
        rows.append(check("rollback-interruption-recorded", partial.get("status") == "rollback_interrupted"))
        recovery = inspect_installation_transaction(runtime_root=runtime)
        rows.append(check("interrupted-rollback-recoverable", recovery.get("ok") and recovery.get("rollback_available")))
        preview2 = preview_installation_rollback(runtime_root=runtime)
        completed = rollback_installation_transaction(str(preview2.get("authorization_token") or ""), confirm=ROLLBACK_CONFIRMATION, runtime_root=runtime)
        rows.append(check("rollback-completes", completed.get("ok") and completed.get("status") == "rolled_back"))
        after = snapshot_files(fixture["target"])
        rows.append(check("rollback-restores-exact-file-state", after == before))
        status2 = inspect_installation_transaction(runtime_root=runtime)
        rows.append(check("rolled-back-state-stable", status2.get("ok") and status2.get("status") == "rolled_back" and not status2.get("rollback_available")))
        receipt_pointer = read_json(transaction_directory(runtime) / "active_installed_receipt.json")
        receipt = read_json(transaction_directory(runtime) / "installed_receipts" / f"{receipt_pointer.get('transaction_id','')}.json")
        rows.append(check("receipt-preserves-rollback-history", receipt.get("state") == "rolled_back" and receipt.get("rolled_back_at")))

    # External edits after a partial apply are preserved and make outcome uncertain.
    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-6-conflict-") as td:
        fixture = prepare_staged_fixture(Path(td))
        interrupted = begin_apply(fixture, "after_effect:1")
        runtime = fixture["handoff_runtime"]
        pointer = read_json(transaction_directory(runtime) / "active_transaction.json")
        record = read_json(transaction_directory(runtime) / "records" / f"{pointer.get('transaction_id','')}.json")
        completed_path = str((record.get("effects_completed") or [""])[0])
        changed = fixture["target"] / completed_path
        changed.parent.mkdir(parents=True, exist_ok=True)
        changed.write_text("operator external edit after interruption\n", encoding="utf-8")
        external_bytes = changed.read_bytes()
        status = inspect_installation_transaction(runtime_root=runtime)
        rows.append(check("external-edit-makes-outcome-uncertain", not status.get("ok") and status.get("status") == "uncertain"))
        preview = preview_installation_rollback(runtime_root=runtime)
        rows.append(check("conflicted-rollback-not-authorized", not preview.get("ok") and not preview.get("authorization_token")))
        rows.append(check("external-edit-preserved", changed.read_bytes() == external_bytes))

    # A recovery token becomes stale when target state changes after preview.
    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-6-stale-") as td:
        fixture = prepare_staged_fixture(Path(td))
        begin_apply(fixture, "after_backup")
        runtime = fixture["handoff_runtime"]
        preview = preview_installation_resume(runtime_root=runtime)
        token = str(preview.get("authorization_token") or "")
        (fixture["target"] / "README.md").write_text("changed after recovery preview\n", encoding="utf-8")
        rejected = resume_installation_transaction(token, confirm=RESUME_CONFIRMATION, runtime_root=runtime)
        rows.append(check("stale-recovery-token-rejected", not rejected.get("ok") and rejected.get("status") == "resume_rejected"))
        rows.append(check("stale-recovery-preserves-edit", (fixture["target"] / "README.md").read_text(encoding="utf-8") == "changed after recovery preview\n"))

    report = {
        "suite": "v1096.6-interrupted-installation-recovery-and-rollback",
        "passed": sum(bool(row["ok"]) for row in rows),
        "failed": sum(not bool(row["ok"]) for row in rows),
        "checks": rows,
    }
    report["ok"] = report["failed"] == 0
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
