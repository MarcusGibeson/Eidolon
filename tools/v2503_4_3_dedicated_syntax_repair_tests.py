from __future__ import annotations

import contextlib
import io
import json
import runpy
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

from isolated_coding_execution import _syntax_repair_prompt
from evidence_to_candidate_planner import build_evidence_to_candidate_plans
from product_plan_lifecycle import process_product_plan_control, register_product_candidate_plan


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


with contextlib.redirect_stdout(io.StringIO()):
    runpy.run_path(str(ROOT / "tools" / "v2503_4_2_one_command_product_repair_cycle_tests.py"), run_name="__main__")

candidate = json.dumps({"edits": [{"path": "conscious_agent/example.py", "replacements": [{"old": "return 1", "new": "return ("}]}], "creates": []})
with tempfile.TemporaryDirectory(prefix="eid-v2503-4-3-diagnostics-") as directory:
    syntax_root = Path(directory)
    (syntax_root / "conscious_agent").mkdir()
    (syntax_root / "conscious_agent" / "example.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    prompt = json.loads(_syntax_repair_prompt(
        root=syntax_root,
        request_id="devc_test",
        execution_digest="a" * 64,
        attempt_number=2,
        rejected_candidate_json=candidate,
    ))

checks = {
    "dedicated_mode": prompt.get("mode") == "syntax_repair",
    "exact_candidate_carried": prompt.get("rejected_candidate_json") == candidate,
    "execution_binding_preserved": prompt.get("authority", {}).get("execution_digest") == "a" * 64,
    "attempt_binding_preserved": prompt.get("authority", {}).get("attempt") == 2,
    "full_source_context_excluded": "workspace_files" not in prompt,
    "same_paths_only": prompt.get("limits", {}).get("same_paths_only") is True,
    "application_denied": prompt.get("authority", {}).get("selected_project_application_authorized") is False,
    "syntax_failure_path_identified": prompt.get("syntax_diagnostics", [{}])[0].get("path") == "conscious_agent/example.py",
    "syntax_failure_location_identified": prompt.get("syntax_diagnostics", [{}])[0].get("line") == 2,
    "syntax_failure_excerpt_bounded": "return (" in prompt.get("syntax_diagnostics", [{}])[0].get("candidate_excerpt", ""),
    "v2503_4_2_behavior_retained": True,
}
for label, passed in checks.items():
    require(passed, label)

with tempfile.TemporaryDirectory(prefix="eid-v2503-4-3-retry-") as directory:
    base = Path(directory)
    source = base / "source"
    runtime = base / "runtime"
    (source / "conscious_agent").mkdir(parents=True)
    (source / "tools").mkdir()
    (source / "conscious_agent" / "discourse_response_planning.py").write_text("def target():\n    return 'current'\n", encoding="utf-8")
    (source / "conscious_agent" / "conversation_context.py").write_text("def context():\n    return []\n", encoding="utf-8")
    (source / "conscious_agent" / "context_assembly_architecture.py").write_text("def assemble():\n    return []\n", encoding="utf-8")
    (source / "tools" / "conversation_target_tests.py").write_text("print('ok')\n", encoding="utf-8")
    evidence = {
        "evidence_id": "initev_" + "c" * 24,
        "evidence_digest": "d" * 64,
        "evidence_class": "conversation_quality_finding",
        "issue_domain": "model_quality",
        "impact_score": 0.8,
        "confidence": 0.9,
        "freshness": "current",
        "structural_only": False,
    }
    plan = build_evidence_to_candidate_plans({"records": [evidence]}, source_root=source)["plans"][0]
    register_product_candidate_plan(plan, source_root=source, runtime_root=runtime)
    phrase = f"Run one supervised product repair cycle for {plan['candidate_plan_id']} digest {plan['candidate_plan_digest'][:16]}."
    invalid = json.dumps({"edits": [{"path": "conscious_agent/discourse_response_planning.py", "replacements": [{"old": "return 'current'", "new": "return ("}]}], "creates": []})
    first = process_product_plan_control(phrase, source_root=source, runtime_root=runtime, provider_generate=lambda _prompt: invalid, python_executable=sys.executable)
    require(first.get("ok") is False and first.get("status") == "isolated_coding_generation_rejected", "stopped_cycle_is_recorded")
    first_request_id = first.get("request_id")

    regression_path = f"tools/product_repair_{plan['candidate_plan_id'].removeprefix('devplan_')}_tests.py"
    valid = json.dumps({
        "edits": [{"path": "conscious_agent/discourse_response_planning.py", "replacements": [{"old": "return 'current'", "new": "return 'repaired'"}]}],
        "creates": [{"path": regression_path, "content": "assert True\n"}],
    })
    second = process_product_plan_control(phrase, source_root=source, runtime_root=runtime, provider_generate=lambda _prompt: valid, python_executable=sys.executable)
    require(second.get("ok") is True and second.get("status") == "product_repair_candidate_ready", "stopped_cycle_can_retry_to_completion")
    require(second.get("request_id") != first_request_id, "retry_receives_new_lineage_bound_request")
    require(second.get("source_modified") is False, "retry_preserves_active_source")
    checks.update({
        "stopped_cycle_is_recorded": True,
        "stopped_cycle_can_retry_to_completion": True,
        "retry_receives_new_lineage_bound_request": True,
        "retry_preserves_active_source": True,
    })

print(json.dumps({
    "suite": "v2503.4.3-dedicated-syntax-repair",
    "ok": True,
    "passed": len(checks),
    "failed": 0,
    "checks": list(checks),
    "source_modified": False,
    "application_authorized": False,
    "installation_authorized": False,
}, sort_keys=True))
