from __future__ import annotations

"""Integrated v1253 Runtime Efficiency Beta contract."""

import hashlib
import json
from pathlib import Path
from typing import Any

from performance_budgets import performance_budgets
from performance_regression import build_performance_regression_receipt

CONTRACT_VERSION="v1253.8"
MILESTONE_NAME="Runtime Efficiency Beta"
VERSION_PLAN=(
    ("1253.0","Critical-Path Cognition Split"),
    ("1253.1","Bounded Internal Maintenance Queue"),
    ("1253.2","Work Coalescing"),
    ("1253.3","Import Graph Audit and Lazy Loading"),
    ("1253.4","Self-Maintenance Decomposition II"),
    ("1253.5","API/Dashboard Dependency Isolation"),
    ("1253.6","Explicit Performance Budgets"),
    ("1253.7","Performance Regression Harness"),
    ("1253.8","Integrated Real-Use Performance Benchmark"),
)
AUTHORITY_FLAGS={
    "installation_authorized":False,"promotion_authorized":False,"certification_authorized":False,
    "release_authorized":False,"provider_contact_authorized":False,"tool_execution_authorized":False,
    "project_mutation_authorized":False,"source_mutation_authorized":False,"approval_granted":False,
    "independent_authority_granted":False,
}

def _digest(value:object)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def runtime_efficiency_beta_contract(*,source_root:str|Path|None=None)->dict[str,Any]:
    root=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    names=(
        "critical_path_runtime.py","goal_planning_bundle.py","bounded_internal_maintenance.py","work_coalescing.py",
        "self_maintenance_attention_primitives.py","dashboard_fast_status.py","performance_budgets.py",
        "performance_regression.py","runtime_efficiency_benchmark.py",
    )
    files={name:root/"conscious_agent"/name for name in names}
    conversation=(root/"conscious_agent/conversation_runtime.py").read_text(encoding="utf-8")
    launcher=(root/"conscious_agent/chat_launcher.py").read_text(encoding="utf-8")
    dashboard=(root/"conscious_agent/dashboard.py").read_text(encoding="utf-8")
    self_maintenance=(root/"conscious_agent/self_maintenance.py").read_text(encoding="utf-8")
    budgets=performance_budgets()
    regression=build_performance_regression_receipt({"warm_pre_provider_ms":[12,13,14,15,16]})
    checks={
        "all_nine_units_declared":len(VERSION_PLAN)==9 and VERSION_PLAN[0][0]=="1253.0" and VERSION_PLAN[-1][0]=="1253.8",
        "all_runtime_modules_present":all(path.is_file() for path in files.values()),
        "planning_stack_lazy":"goal_planning_bundle" in conversation and "from hierarchical_planning_runtime import" not in conversation,
        "deferred_planning_completed_post_provider":"_complete_deferred_goal_planning" in conversation,
        "housekeeping_bounded":"schedule_post_turn_housekeeping" in conversation,
        "turn_work_coalescing":"TurnWorkCache" in conversation,
        "chat_runtime_import_lazy":launcher.index("from conversation_runtime import")>launcher.index("user_message = input"),
        "self_maintenance_primitives_extracted":"self_maintenance_attention_primitives" in self_maintenance,
        "dashboard_fast_status_isolated":"/api/runtime-status" in dashboard and "dashboard_fast_status" in dashboard,
        "performance_budgets_defined":len(budgets["budgets"])>=10,
        "regression_harness_uses_median_p95":regression["median_and_p95_used"] is True,
        "authority_remains_denied":not any(AUTHORITY_FLAGS.values()),
    }
    result={"ok":all(checks.values()),"status":"runtime_efficiency_beta_ready" if all(checks.values()) else "runtime_efficiency_beta_blocked","contract_version":CONTRACT_VERSION,"milestone_name":MILESTONE_NAME,"versions":[{"version":v,"title":t} for v,t in VERSION_PLAN],"checks":checks,"passed":sum(checks.values()),"total":len(checks),"read_only":True,"content_free":True,**AUTHORITY_FLAGS}
    result["contract_digest"]=_digest(result); return result

__all__=["CONTRACT_VERSION","MILESTONE_NAME","VERSION_PLAN","AUTHORITY_FLAGS","runtime_efficiency_beta_contract"]
