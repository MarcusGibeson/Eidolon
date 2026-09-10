from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v1500-0-1-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME / "runtime")
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "conscious_agent")]

from conscious_agent import generalized_isolated_coding as coding
from conscious_agent.autonomous_developer_v1500 import REQUIRED_CAPABILITIES, build_autonomous_developer_benchmark
from conscious_agent.development_authority import issue_operator_authorization, private_scope_digest, validate_operator_authorization
from conscious_agent.dynamic_development_backlog import DynamicDevelopmentBacklog
from conscious_agent.dynamic_implementation_planning import build_evidence_bound_plan
from conscious_agent.governed_candidate_review import admit_operator_installation, installation_preview
from conscious_agent.windows_certification_protocol import REQUIRED_NATIVE_CHECKS, build_windows_certification_protocol, evaluate_windows_receipts


passed = failed = 0


def check(name: str, condition: bool, detail: object = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print("PASS", name)
    else:
        failed += 1
        print("FAIL", name, detail)


try:
    phrase = "Select candidate candidate-a."
    selection = issue_operator_authorization(
        stage="candidate_selection",
        subject_id="candidate-a",
        subject_digest="a" * 64,
        explicit_operator_text=phrase,
        expected_operator_text=phrase,
    )
    check("exact operator command creates sealed receipt", validate_operator_authorization(selection, stage="candidate_selection", subject_id="candidate-a", subject_digest="a" * 64)["ok"], selection)
    tampered = dict(selection)
    tampered["subject_id"] = "candidate-b"
    check("tampered authorization receipt fails closed", not validate_operator_authorization(tampered, stage="candidate_selection", subject_id="candidate-b", subject_digest="a" * 64)["ok"], tampered)

    candidate = {
        "candidate_id": "candidate-a",
        "evidence_digest": "b" * 64,
        "eligibility_digest": "a" * 64,
        "source_module": "conscious_agent/sample.py",
        "proposed_destination_module": "conscious_agent/sample_helpers.py",
        "source_symbols": ["alpha", "beta"],
        "eligible_for_quality_comparison": True,
    }
    forged_plan = build_evidence_bound_plan(candidate, operator_selection_receipt={"authorized": True})
    check("plain authorization boolean cannot create plan", not forged_plan["plan_created"], forged_plan)
    plan = build_evidence_bound_plan(candidate, operator_selection_receipt=selection)
    check("sealed candidate selection creates bounded plan", plan["plan_created"], plan)

    workspace = RUNTIME / "workspace"
    (workspace / "conscious_agent").mkdir(parents=True)
    source = workspace / "conscious_agent" / "sample.py"
    source.write_text("x = 1\ny = 1\n", encoding="utf-8")
    destination = workspace / "conscious_agent" / "sample_helpers.py"
    edits = [
        {"path": "conscious_agent/sample.py", "action": "modify", "replacements": [{"find": "x = 1", "replace": "x = 2"}]},
        {"path": "conscious_agent/sample_helpers.py", "action": "create", "content": "VALUE = 2\n"},
    ]
    workspace_phrase = "Implement candidate candidate-a."
    workspace_receipt = issue_operator_authorization(
        stage="workspace_implementation",
        subject_id="candidate-a",
        subject_digest=plan["plan_digest"],
        scope_digest=private_scope_digest(str(workspace.resolve())),
        explicit_operator_text=workspace_phrase,
        expected_operator_text=workspace_phrase,
    )
    blocked = coding.apply_structured_edits(workspace, plan, edits, workspace_authorization_receipt={"authorized": True})
    check("plain workspace authorization boolean cannot edit", blocked["status"] == "blocked" and source.read_text(encoding="utf-8") == "x = 1\ny = 1\n", blocked)

    original_replace = coding.os.replace
    calls = 0

    def fail_second_replace(source_path, destination_path):
        nonlocal_calls[0] += 1
        if nonlocal_calls[0] == 2:
            raise OSError("synthetic second write failure")
        return original_replace(source_path, destination_path)

    nonlocal_calls = [0]
    coding.os.replace = fail_second_replace
    try:
        try:
            coding.apply_structured_edits(workspace, plan, edits, workspace_authorization_receipt=workspace_receipt)
        except OSError:
            pass
    finally:
        coding.os.replace = original_replace
    check("multi-file write failure rolls back earlier edit", source.read_text(encoding="utf-8") == "x = 1\ny = 1\n" and not destination.exists())

    backlog = DynamicDevelopmentBacklog(RUNTIME / "backlog")
    backlog.ingest_comparison("ingest", {"comparison_digest": "c" * 64, "ordered_comparison": [{"candidate_id": "candidate-a", "quality_score": 1.0}]})
    jumped = backlog.transition("jump", "candidate-a", "installed", evidence_digest="d" * 64, operator_authorization_receipt={"authorized": True})
    check("backlog rejects direct discovered-to-installed jump", jumped["reason"] == "illegal_state_transition", jumped)

    protocol = build_windows_certification_protocol(candidate_zip_sha256="a" * 64, source_manifest_sha256="b" * 64)
    forged_windows = evaluate_windows_receipts(protocol, [{"check": name, "passed": True, "platform": "Windows"} for name in REQUIRED_NATIVE_CHECKS])
    check("unsealed Windows rows cannot complete native evidence", not forged_windows["evidence_complete"] and forged_windows["invalid_receipt_count"] == len(REQUIRED_NATIVE_CHECKS), forged_windows)

    forged_benchmark = build_autonomous_developer_benchmark([{"capability": name, "passed": True} for name in REQUIRED_CAPABILITIES])
    check("self-asserted capability rows cannot pass v1500", not forged_benchmark["deterministic_benchmark_passed"], forged_benchmark)

    preview = installation_preview({"review_ready": True, "review_digest": "c" * 64, "candidate_id": "candidate-a"}, authoritative_source_digest="a" * 64, candidate_source_digest="b" * 64)
    forged_install = admit_operator_installation(preview, operator_authorization_receipt={"authorized": True}, expected_preview_digest=preview["preview_digest"])
    check("plain installation approval boolean cannot admit installer", not forged_install["admitted_for_external_installer"], forged_install)

    print({"ok": failed == 0, "passed": passed, "failed": failed, "suite": "v1500.0.1-authority-integration-repair", "content_free": True})
finally:
    shutil.rmtree(RUNTIME, ignore_errors=True)

if failed:
    raise SystemExit(1)
