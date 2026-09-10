from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for value in (ROOT, ROOT / "conscious_agent"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from evidence_to_candidate_planner import build_evidence_to_candidate_plans
from product_plan_lifecycle import process_product_plan_control, register_product_candidate_plan


checks: list[str] = []


def require(value: object, label: str) -> None:
    if not value:
        raise AssertionError(label)
    checks.append(label)


def tree_digest(root: Path) -> str:
    rows = [
        (path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    ]
    return hashlib.sha256(json.dumps(rows).encode("utf-8")).hexdigest()


with tempfile.TemporaryDirectory(prefix="eid-v2503-4-2-cycle-") as directory:
    base = Path(directory)
    source = base / "source"
    runtime = base / "runtime"
    (source / "conscious_agent").mkdir(parents=True)
    (source / "tools").mkdir()
    (source / "conscious_agent" / "discourse_response_planning.py").write_text(
        "def target():\n    return 'current'\n", encoding="utf-8"
    )
    (source / "conscious_agent" / "conversation_context.py").write_text(
        "def context():\n    return []\n", encoding="utf-8"
    )
    (source / "conscious_agent" / "context_assembly_architecture.py").write_text(
        "def assemble():\n    return []\n", encoding="utf-8"
    )
    (source / "tools" / "conversation_target_tests.py").write_text("print('ok')\n", encoding="utf-8")
    evidence = {
        "evidence_id": "initev_" + "a" * 24,
        "evidence_digest": "b" * 64,
        "evidence_class": "conversation_quality_finding",
        "issue_domain": "model_quality",
        "impact_score": 0.8,
        "confidence": 0.9,
        "freshness": "current",
        "structural_only": False,
    }
    plan = build_evidence_to_candidate_plans({"records": [evidence]}, source_root=source)["plans"][0]
    registered = register_product_candidate_plan(plan, source_root=source, runtime_root=runtime)
    require(registered["ok"], "product_plan_is_registered")
    before = tree_digest(source)
    provider_calls: list[str] = []

    def provider(prompt: str) -> str:
        provider_calls.append(prompt)
        if len(provider_calls) == 1:
            return json.dumps({
                "edits": [{
                    "path": "conscious_agent/discourse_response_planning.py",
                    "replacements": [{"old": "return 'current'", "new": "return ("}],
                }],
                "creates": [],
            })
        repair_prompt = json.loads(prompt)
        require(repair_prompt.get("mode") == "syntax_repair", "syntax_retry_uses_dedicated_minimal_prompt")
        require("workspace_files" not in repair_prompt, "syntax_retry_does_not_repeat_full_source_context")
        require(
            bool(repair_prompt.get("rejected_candidate_json")),
            "syntax_retry_receives_transient_rejected_candidate",
        )
        return json.dumps({
            "edits": [{
                "path": "conscious_agent/discourse_response_planning.py",
                "replacements": [{"old": "return 'current'", "new": "return 'repaired'"}],
            }],
            "creates": [{
                "path": f"tools/product_repair_{plan['candidate_plan_id'].removeprefix('devplan_')}_tests.py",
                "content": "assert True\n",
            }],
        })

    phrase = (
        f"Run one supervised product repair cycle for {plan['candidate_plan_id']} "
        f"digest {plan['candidate_plan_digest'][:16]}."
    )
    result = process_product_plan_control(
        phrase,
        source_root=source,
        runtime_root=runtime,
        provider_generate=provider,
        python_executable=sys.executable,
    )
    require(result["active"] and result["ok"], "one_command_cycle_completes")
    require(result["status"] == "product_repair_candidate_ready", "one_command_cycle_returns_reviewable_candidate")
    require(len(provider_calls) == 2, "one_command_cycle_uses_one_bounded_syntax_repair")
    require(result["tests_executed"], "one_command_cycle_runs_bounded_verification")
    require(result["isolated_coding_execution"]["test_passed"] is True, "one_command_cycle_passes_verification")
    require(result["isolated_coding_execution"]["changed_file_count"] == 2, "one_command_cycle_seals_bounded_diff")
    require("consumed the exact isolated execution authorization" in result["conversation_response"], "execution_authorization_is_included")
    require(not result["application_authorized"] and not result["installation_authorized"], "application_and_installation_remain_separate")
    require(before == tree_digest(source), "one_command_cycle_preserves_active_source")

    replay = process_product_plan_control(
        phrase,
        source_root=source,
        runtime_root=runtime,
        provider_generate=lambda _prompt: (_ for _ in ()).throw(AssertionError("provider replayed")),
        python_executable=sys.executable,
    )
    require(replay["ok"] and replay["status"] == "product_repair_candidate_ready", "completed_cycle_replay_is_idempotent")
    require(len(provider_calls) == 2, "completed_cycle_replay_does_not_contact_provider")

    stale = process_product_plan_control(
        f"Run one supervised product repair cycle for {plan['candidate_plan_id']} digest {'0' * 16}.",
        source_root=source,
        runtime_root=runtime,
        provider_generate=lambda _prompt: (_ for _ in ()).throw(AssertionError("stale provider call")),
    )
    require(not stale["ok"] and stale["status"] == "product_plan_missing_or_stale", "stale_cycle_digest_fails_before_execution")
    require(not stale["source_modified"] and not stale["authority_granted"], "stale_cycle_grants_no_authority")
    require(bool(stale.get("conversation_response")), "blocked_cycle_returns_deterministic_conversation_response")
    require("did not run" in stale["conversation_response"], "blocked_cycle_explains_non_execution")

    (source / "conscious_agent" / "conversation_context.py").write_text(
        "def context():\n    return ['changed']\n", encoding="utf-8"
    )
    source_stale = process_product_plan_control(
        phrase,
        source_root=source,
        runtime_root=runtime,
        provider_generate=lambda _prompt: (_ for _ in ()).throw(AssertionError("stale source provider call")),
    )
    require(not source_stale["ok"] and source_stale["status"] == "product_plan_source_stale", "source_stale_cycle_fails_before_execution")
    require("bound source snapshot is stale" in source_stale["conversation_response"], "source_stale_cycle_explains_rebinding")
    require(not source_stale["provider_contacted"] and not source_stale["tests_executed"], "source_stale_cycle_executes_nothing")

    inactive = process_product_plan_control(
        "Continue your supervised development.", source_root=source, runtime_root=runtime
    )
    require(inactive["active"] is False, "generic_continuation_does_not_authorize_product_cycle")

print(json.dumps({
    "ok": True,
    "suite": "v2503.4.2-one-command-product-repair-cycle",
    "passed": len(checks),
    "failed": 0,
    "checks": checks,
    "source_modified": False,
    "installation_authorized": False,
    "release_authorized": False,
}, sort_keys=True))
