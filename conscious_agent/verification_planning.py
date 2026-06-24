from __future__ import annotations

from typing import Any

VERIFICATION_PLANNING_VERSION = "500.0"

DEFAULT_VERIFICATION_STEPS = [
    {"name": "compile", "command": "python -m compileall conscious_agent tools", "runs_automatically": False},
    {"name": "fast-smoke", "command": "python tools/smoke_check.py --tier fast --json", "runs_automatically": False},
    {"name": "install-smoke", "command": "python tools/smoke_check.py --tier install --json", "runs_automatically": False},
    {"name": "package-privacy", "command": "python conscious_agent/main.py --package-privacy-scan --readiness-json", "runs_automatically": False},
    {"name": "extracted-zip-fast-smoke", "command": "python tools/smoke_check.py --tier fast --json", "runs_automatically": False},
    {"name": "extracted-zip-install-smoke", "command": "python tools/smoke_check.py --tier install --json", "runs_automatically": False},
    {"name": "dashboard-tooltip", "command": "manual/dashboard route check for data-tip and no native nav title", "runs_automatically": False},
]

def build_verification_readiness_plan(scope: str = "self-maintenance-decomposition") -> dict[str, Any]:
    return {
        "version": VERIFICATION_PLANNING_VERSION,
        "scope": scope,
        "steps": list(DEFAULT_VERIFICATION_STEPS),
        "step_count": len(DEFAULT_VERIFICATION_STEPS),
        "runs_commands": False,
        "executes_smoke": False,
        "authorizes_release": False,
        "ok": True,
    }

def verification_readiness_summary(plan: dict[str, Any] | None = None) -> list[str]:
    plan = plan or build_verification_readiness_plan()
    return [f"- {step.get('name')}: {step.get('command')} (runs automatically: {step.get('runs_automatically', False)})" for step in plan.get("steps", [])]
