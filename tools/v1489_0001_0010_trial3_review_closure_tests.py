from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

import conversation_runtime
import dashboard_chat_console as dashboard
from conversation_context import build_conversation_prompt
from conversation_sessions import create_conversation_session, append_conversation_turn
from desktop_shell import _desktop_stream_text
from immediate_conversation_grounding import build_immediate_conversation_grounding

CHECKS: list[tuple[str, bool, object]] = []


def require(name: str, condition: object, detail: object = "") -> None:
    CHECKS.append((name, bool(condition), detail))
    if not condition:
        raise AssertionError(f"{name}: {detail}")


def _source_manifest() -> dict[str, str]:
    rows: dict[str, str] = {}
    excluded = {"data", ".git", ".venv", "__pycache__"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in excluded for part in path.relative_to(ROOT).parts):
            continue
        rows[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return rows


def _unsupported_question() -> str:
    return "What difficulties have we had with synthetic archive planning, and what evidence supports that?"


def _compound_correction() -> str:
    return (
        "I need to correct you: the synthetic diagnosis was River rash, and Lumen was not the cause. "
        "Tell me exactly what I just corrected."
    )


def test_metrics_and_provenance_consistency() -> None:
    grounding = build_immediate_conversation_grounding(_unsupported_question(), [], [])
    summary = grounding.public_summary()
    require("0001-uncertainty-public", summary.get("historical_uncertainty_required") is True, summary)
    require("0002-evidence-class-counts-public", isinstance(summary.get("historical_evidence_class_counts"), dict), summary)
    require("0003-provenance-digest-public", len(str(summary.get("historical_provenance_state_digest") or "")) == 24, summary)
    encoded = json.dumps(summary, sort_keys=True)
    for private in ("archive planning", "What difficulties", "synthetic diagnosis"):
        require(f"metrics-content-free:{private[:8]}", private not in encoded, encoded)

    packet = build_conversation_prompt(
        user_message=_unsupported_question(),
        self_model={"name": "Eidolon"}, desires={}, memories=[],
        project_context="", goal_context="", task_context="", conversation_history=[],
        context_size=4096, max_tokens=300, natural_follow_up_policy=None,
    )
    metrics = packet.metrics.to_dict()
    require("0001-context-uncertainty", metrics.get("historical_uncertainty_required") is True, metrics)
    require("0002-context-counts", isinstance(metrics.get("historical_evidence_class_counts"), dict), metrics)
    require("0003-context-digest", metrics.get("historical_provenance_state_digest") == summary.get("historical_provenance_state_digest"), metrics)


def test_release_registration_and_v1175_behavioral_fixture() -> None:
    source = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
    require("0004-trial3-registered-once", source.count("v1489-trial3-compound-grounding-memory-truth") == 1)
    stale = (ROOT / "tools" / "v1175_0_2_natural_language_action_routing_tests.py").read_text(encoding="utf-8")
    require("0005-no-stale-call-count-assertion", "stream-nonstream-projection-count" not in stale)
    require("0005-behavioral-parity-present", "routing-behavior-parity" in stale)


def test_dashboard_current_correction_precedence() -> None:
    session = create_conversation_session(title="Bundle1 correction", select_session=False)
    append_conversation_turn(
        session["id"], turn_id="b1_prev", user_message="What did we discuss before?",
        assistant_response="I am uncertain.", completion_state="completed", success=True,
        source="v1489_bundle1_fixture", select_session=False,
    )
    original = dashboard.run_conversation_turn
    try:
        turn = dashboard.create_dashboard_chat_turn(_compound_correction(), use_ai=True, session_id=session["id"])
    finally:
        dashboard.run_conversation_turn = original
    response = str(turn.get("eidolon_response") or "")
    require("0006-dashboard-current-correction", "River rash" in response and "Lumen" in response, response)
    require("0006-dashboard-no-prior-question-echo", "What did we discuss before" not in response, response)
    runtime = turn.get("conversation_runtime") or {}
    require("0006-dashboard-provider-zero", runtime.get("provider_request_count") == 0, runtime)


def test_desktop_uncertainty_receipt_and_reconnect_non_evidence() -> None:
    session = create_conversation_session(title="Bundle1 history", select_session=False)
    append_conversation_turn(
        session["id"], turn_id="b1_assistant", user_message="Can you explain reminders?",
        assistant_response="I can help with synthetic archive planning and reminder tools.",
        completion_state="completed", success=True, source="v1489_bundle1_fixture", select_session=False,
    )
    acceptance_key = "bundle1-history-acceptance-001"
    accepted = dashboard.start_dashboard_chat_operation(
        _unsupported_question(), use_ai=True, session_id=session["id"], acceptance_key=acceptance_key,
    )
    duplicate = dashboard.start_dashboard_chat_operation(
        _unsupported_question(), use_ai=True, session_id=session["id"], acceptance_key=acceptance_key,
    )
    require("0008-duplicate-acceptance-reused", duplicate.get("duplicate_acceptance") is True, duplicate)
    require("0008-reconnect-same-operation", accepted["operation"]["operation_id"] == duplicate["operation"]["operation_id"], (accepted, duplicate))
    events = list(dashboard.subscribe_dashboard_chat_operation(accepted["operation"]["operation_id"]))
    done = next(row for row in events if row.get("event") == "done")
    turn = done.get("turn") or {}
    mode, text = _desktop_stream_text(done)
    require("0007-desktop-visible-uncertainty", mode == "replace" and ("don't have" in text.lower() or "not evidence" in text.lower() or "uncertain" in text.lower()), (mode, text))
    context = ((turn.get("conversation_runtime") or {}).get("context") or {})
    require("0007-desktop-uncertainty-metric", context.get("historical_uncertainty_required") is True, context)
    require("0007-desktop-content-free-digest", len(str(context.get("historical_provenance_state_digest") or "")) == 24, context)
    require("0008-assistant-non-evidence-count", int((context.get("historical_evidence_class_counts") or {}).get("assistant_authored_non_evidence", 0)) >= 1, context)
    require("0008-provider-zero", (turn.get("conversation_runtime") or {}).get("provider_request_count") == 0, turn)


def test_trial3_execution_source_immutable_and_private_external() -> None:
    before = _source_manifest()
    with tempfile.TemporaryDirectory(prefix="eidolon-v1489-b1-") as runtime:
        env = dict(os.environ)
        env["EIDOLON_DATA_DIR"] = runtime
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [sys.executable, "-B", str(ROOT / "tools" / "v1489_trial3_compound_grounding_memory_truth_tests.py")],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=180,
        )
        require("0009-trial3-subprocess-pass", proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:])
        runtime_paths = [p.relative_to(runtime).as_posix() for p in Path(runtime).rglob("*") if p.is_file()]
        require("0009-runtime-external", all(not (ROOT / rel).exists() for rel in runtime_paths), runtime_paths[:20])
    after = _source_manifest()
    require("0009-source-immutable", before == after, {"before": len(before), "after": len(after)})
    forbidden = [rel for rel in after if rel.startswith("data/") or "__pycache__" in rel or rel.endswith(".pyc")]
    require("0009-source-privacy", not forbidden, forbidden)


def main() -> None:
    tests = [
        test_metrics_and_provenance_consistency,
        test_release_registration_and_v1175_behavioral_fixture,
        test_dashboard_current_correction_precedence,
        test_desktop_uncertainty_receipt_and_reconnect_non_evidence,
        test_trial3_execution_source_immutable_and_private_external,
    ]
    for test in tests:
        test()
    print(f"v1489.0001-.0010 Trial 3 review closure: {len(CHECKS)}/{len(CHECKS)} checks passed")
    for name, ok, _detail in CHECKS:
        print(f"  {'PASS' if ok else 'FAIL'} {name}")


if __name__ == "__main__":
    main()
