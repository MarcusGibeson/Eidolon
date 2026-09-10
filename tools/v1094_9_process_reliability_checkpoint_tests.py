from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

RESULTS: list[dict[str, object]] = []


def require(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check(name: str, fn) -> None:
    try:
        fn()
        RESULTS.append({"name": name, "ok": True})
    except Exception as exc:
        RESULTS.append({"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})


def _base_operation(*, may_mutate: bool = False, project: str = "eidolon", session: str = "session-a", tab: str = "tab-a", revision: int = 4):
    from process_ownership import accept_process_operation, activate_process_operation

    operation_id = f"checkpoint_{uuid.uuid4().hex}"
    accepted = accept_process_operation(
        operation_id,
        operation_kind="checkpoint",
        may_mutate=may_mutate,
        acceptance_key=operation_id,
        project_id=project,
        session_id=session,
        tab_id=tab,
        tab_revision=revision,
    )
    require(accepted.get("ok"), f"accept failed: {accepted}")
    active = activate_process_operation(operation_id, 1)
    require(active.get("ok"), f"activation failed: {active}")
    return operation_id, str(active["owner_nonce"])


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="eidolon-v1094-9-") as td:
        runtime = Path(td) / "runtime"
        os.environ["EIDOLON_PROCESS_RUNTIME_ROOT"] = str(runtime)
        os.environ["EIDOLON_METADATA_LOCK_DIR"] = str(Path(td) / "locks")

        from process_ownership import (
            accept_process_operation,
            finalize_process_operation,
            inspect_process_operation,
            process_is_alive,
            write_process_result,
        )
        from process_recovery import (
            build_unified_process_recovery_state,
            cancel_process_operation_with_escalation,
            inspect_process_operation_for_context,
            reconcile_process_operation,
        )

        def spawn_contract() -> None:
            source = (AGENT / "process_worker_entrypoints.py").read_text(encoding="utf-8")
            tree = ast.parse(source)
            functions = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
            require("run_bounded_command_worker" in functions, "module-level spawn worker missing")
            require("multiprocessing.get_context(\"spawn\")" in source, "spawn context not explicit")
            require("_filtered_environment" in source and "validate_process_worker_config" in source, "explicit filtered configuration missing")

        def exactly_once_and_pid_identity() -> None:
            op = f"once_{uuid.uuid4().hex}"
            key = uuid.uuid4().hex
            first = accept_process_operation(op, operation_kind="checkpoint", may_mutate=True, acceptance_key=key)
            duplicate = accept_process_operation(op, operation_kind="checkpoint", may_mutate=True, acceptance_key=key)
            reused = accept_process_operation(op, operation_kind="checkpoint", may_mutate=True, acceptance_key="different")
            require(first.get("ok") and duplicate.get("duplicate"), "same acceptance was not idempotent")
            require(reused.get("status") in {"already_owned", "operation_id_reuse_rejected"}, "operation ID reuse accepted")
            require(process_is_alive(os.getpid(), "definitely-not-this-process") is False, "PID reuse identity failed open")

        def cancellation_public_success_contract() -> None:
            op, nonce = _base_operation(may_mutate=False)

            def finish() -> None:
                time.sleep(0.04)
                write_process_result(op, generation=1, owner_nonce=nonce, state="cancelled", applied=False)
                finalize_process_operation(op, 1, nonce, state="cancelled")

            threading.Thread(target=finish, daemon=True).start()
            result = cancel_process_operation_with_escalation(
                op,
                generation=1,
                project_id="eidolon",
                session_id="session-a",
                tab_id="tab-a",
                tab_revision=4,
                operator_confirmed=True,
                cooperative_wait_seconds=0.5,
            )
            require(result.get("ok") is True, f"successful public cancellation lost ok: {result}")
            require(result.get("status") == "cancelled" and result.get("safe_retry") is True, "cancel result misclassified")
            encoded = json.dumps(result, sort_keys=True)
            require("owner_nonce" not in encoded and "child_start_identity" not in encoded, "private cancellation details leaked")

        def stale_and_cross_context_rejected() -> None:
            op, nonce = _base_operation(may_mutate=False)
            stale = cancel_process_operation_with_escalation(
                op,
                generation=2,
                project_id="eidolon",
                session_id="session-a",
                tab_id="tab-a",
                tab_revision=4,
                operator_confirmed=True,
                cooperative_wait_seconds=0,
            )
            require(stale.get("ok") is False and stale.get("stale_request") is True, f"stale request contract lost: {stale}")
            wrong = inspect_process_operation_for_context(
                op, project_id="other", session_id="session-a", tab_id="tab-a", tab_revision=4
            )
            require(wrong.get("project_mismatch") and not wrong.get("control_context_matches"), "cross-project control accepted")
            finalize_process_operation(op, 1, nonce, state="interrupted")

        def result_after_cancel_authoritative() -> None:
            op, nonce = _base_operation(may_mutate=True)

            def finish() -> None:
                time.sleep(0.04)
                write_process_result(op, generation=1, owner_nonce=nonce, state="completed", applied=True)
                finalize_process_operation(op, 1, nonce, state="completed")

            threading.Thread(target=finish, daemon=True).start()
            result = cancel_process_operation_with_escalation(
                op,
                generation=1,
                project_id="eidolon",
                session_id="session-a",
                tab_id="tab-a",
                tab_revision=4,
                operator_confirmed=True,
                cooperative_wait_seconds=0.5,
            )
            require(result.get("ok") is True and result.get("status") == "completed", f"applied result lost: {result}")
            require(result.get("result_after_cancel") is True and result.get("safe_retry") is False, "applied result became retryable")

        def orphan_and_uncertain_boundaries() -> None:
            op, nonce = _base_operation(may_mutate=True)
            finalized = finalize_process_operation(op, 1, nonce, state="uncertain")
            require(finalized.get("state") == "uncertain", "mutating uncertainty not retained")
            state = reconcile_process_operation(op, terminate_orphan=False)
            require(state.get("status") == "uncertain" and state.get("safe_retry") is False, "uncertain mutation became retryable")
            require(state.get("replay_allowed") is False, "uncertain operation replay allowed")

        def restart_and_stale_tab_authority() -> None:
            op, nonce = _base_operation(may_mutate=False)
            exact = inspect_process_operation_for_context(
                op, project_id="eidolon", session_id="session-a", tab_id="tab-a", tab_revision=4
            )
            stale = inspect_process_operation_for_context(
                op, project_id="eidolon", session_id="session-a", tab_id="tab-b", tab_revision=5
            )
            require(exact.get("read_only_reattached") and exact.get("control_context_matches"), "exact restart context not restored")
            require(stale.get("read_only_reattached") and stale.get("stale_tab"), "stale tab lost read-only visibility")
            require(not stale.get("cancellation_available") and not stale.get("control_context_matches"), "stale tab inherited authority")
            finalize_process_operation(op, 1, nonce, state="interrupted")

        def unified_state_privacy_and_bound() -> None:
            for index in range(55):
                op = f"history_{index:02d}_{uuid.uuid4().hex}"
                accepted = accept_process_operation(
                    op,
                    operation_kind="history",
                    may_mutate=False,
                    acceptance_key=op,
                    project_id="eidolon",
                    session_id="history-session",
                    tab_id="history-tab",
                    tab_revision=9,
                )
                require(accepted.get("ok"), "history acceptance failed")
            state = build_unified_process_recovery_state(
                project_id="eidolon", session_id="history-session", tab_id="history-tab", tab_revision=9
            )
            require(state.get("history_limit") == 50 and state.get("history_truncated"), "history was not bounded")
            require(len(state.get("rows") or []) == 50 and int(state.get("total_matching_operation_count") or 0) >= 55, f"bounded counts incorrect: {state.get('operation_count')}/{state.get('total_matching_operation_count')}")
            def collect_keys(value):
                keys = set()
                if isinstance(value, dict):
                    for key, nested in value.items():
                        keys.add(str(key))
                        keys.update(collect_keys(nested))
                elif isinstance(value, list):
                    for nested in value:
                        keys.update(collect_keys(nested))
                return keys
            forbidden = {"owner_nonce", "owner_start_identity", "process_start_identity", "child_start_identity", "command", "environment", "output_path", "result_path", "acceptance_key"}
            require(not (collect_keys(state) & forbidden), f"unified state leaked private keys: {collect_keys(state) & forbidden}")

        def dashboard_and_spoken_response_separation() -> None:
            dashboard = (AGENT / "dashboard.py").read_text(encoding="utf-8")
            console = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
            styles = (AGENT / "dashboard_chat_styles.py").read_text(encoding="utf-8")
            require("/api/process-recovery-state" in dashboard and "/api/process-operation/cancel" in dashboard, "process routes missing")
            require("window.setTimeout(refreshProcessRecoveryState, 0)" in console, "process recovery is not asynchronous")
            require("aria-live='polite'" in console and ":focus-visible" in styles and "@media(max-width:700px)" in styles, "accessibility contract missing")
            route = dashboard[dashboard.find('/api/process-operation/cancel'):dashboard.find('/api/process-recovery/reconcile')]
            require("assistant" not in route, "process state injected into spoken response")

        def metadata_and_conversation_boundaries() -> None:
            process_source = (AGENT / "process_ownership.py").read_text(encoding="utf-8")
            metadata_source = (AGENT / "metadata_mutation_coordination.py").read_text(encoding="utf-8")
            require("metadata_mutation_lock" in process_source, "process ownership is not atomically persisted")
            require("EIDOLON_METADATA_LOCK_DIR" in metadata_source, "metadata lock boundary missing")
            require("process_runtime" in process_source and "conversations" not in process_source, "process ownership coupled to conversation payload storage")

        def release_and_project_truth() -> None:
            from release_metadata import NEXT_RECOMMENDED_ARC, RUNTIME_MILESTONE, RUNTIME_VERSION

            require(tuple(map(int, RUNTIME_VERSION.split("."))) >= (1094, 9), RUNTIME_VERSION)
            require(f"v{RUNTIME_VERSION}" in RUNTIME_MILESTONE, RUNTIME_MILESTONE)
            import re
            next_match = re.search(r"v(\d+(?:\.\d+)+)", NEXT_RECOMMENDED_ARC)
            require(next_match and tuple(map(int, next_match.group(1).split("."))) >= (1095, 0), NEXT_RECOMMENDED_ARC)
            settings = json.loads((ROOT / "data/settings.json").read_text(encoding="utf-8"))
            active = json.loads((ROOT / "data/workspaces/active_project.json").read_text(encoding="utf-8"))
            projects = json.loads((ROOT / "data/workspaces/projects.json").read_text(encoding="utf-8"))
            require(settings.get("root_version") == RUNTIME_VERSION and settings.get("version") == RUNTIME_VERSION, "settings version drift")
            require(active.get("root_version") == RUNTIME_VERSION and projects.get("projects", [{}])[0].get("root_version") == RUNTIME_VERSION and projects.get("projects", [{}])[0].get("working_version") == RUNTIME_VERSION, "project version drift")

        def release_history_and_registration() -> None:
            from release_history import parse_release_history_file
            from release_metadata import RUNTIME_VERSION_TAG
            parsed = parse_release_history_file(ROOT / "README_RELEASE_HISTORY.md")
            require(parsed.get("ok"), parsed)
            entries = parsed.get("public_entries") or []
            require(entries and f"v{entries[0].get('version')}" == RUNTIME_VERSION_TAG, "current release is not newest history entry")
            require(parsed.get("duplicate_version_count") == 0, "duplicate release headings")
            require(parsed.get("ordering_violation_count") == 0, "release history out of order")
            registry = (ROOT / "tools/post_review_development_verify.py").read_text(encoding="utf-8")
            require("v1094.9-process-reliability-checkpoint" in registry, "checkpoint suite not registered")

        def source_only_privacy_contract() -> None:
            forbidden_exact = {
                "data/projects.json", "data/tasks.json", "data/memories.json",
            }
            files = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file()}
            require(not (files & forbidden_exact), f"forbidden runtime file present: {files & forbidden_exact}")
            require(not any("__pycache__" in path or path.endswith((".pyc", ".pyo", ".zip")) for path in files), "generated artifact in source")
            require(not any(path.startswith("data/approvals/") or path.startswith("data/conversations/") for path in files), "private runtime directory present")

        checks = [
            ("spawn-safe worker entry points", spawn_contract),
            ("exactly-once and PID identity", exactly_once_and_pid_identity),
            ("public cancellation success contract", cancellation_public_success_contract),
            ("stale and cross-context cancellation", stale_and_cross_context_rejected),
            ("result after cancel remains authoritative", result_after_cancel_authoritative),
            ("orphan and uncertain result boundaries", orphan_and_uncertain_boundaries),
            ("restart visibility without authority transfer", restart_and_stale_tab_authority),
            ("content-free bounded unified recovery", unified_state_privacy_and_bound),
            ("dashboard accessibility and speech separation", dashboard_and_spoken_response_separation),
            ("metadata and conversation boundaries", metadata_and_conversation_boundaries),
            ("release and project truth", release_and_project_truth),
            ("release history and verification registration", release_history_and_registration),
            ("source-only privacy contract", source_only_privacy_contract),
        ]
        for name, fn in checks:
            check(name, fn)

    passed = sum(1 for row in RESULTS if row["ok"])
    report = {
        "version": "1094.9",
        "status": "pass" if passed == len(RESULTS) else "fail",
        "passed": passed,
        "total": len(RESULTS),
        "checks": RESULTS,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
