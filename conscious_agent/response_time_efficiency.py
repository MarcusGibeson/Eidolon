from __future__ import annotations

"""Read-only response-time integration contract for v1251.0-v1251.8.

The contract measures and validates latency-oriented architecture without
contacting providers, executing tools, mutating projects, or granting authority.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

from response_time_runtime import (
    AUTHORITY_FLAGS,
    MAX_COMPACT_COGNITIVE_CHARS,
    build_compact_cognitive_projection,
    generation_token_budget,
    provider_metrics_public,
    trusted_action_acknowledgement,
)
from dashboard_performance import optimize_dashboard_html_assets

CONTRACT_VERSION = "v1251.8"
MILESTONE_NAME = "Response-Time and Runtime Efficiency Alpha"

VERSION_PLAN = (
    ("1251.0", "End-to-End Latency Telemetry"),
    ("1251.1", "Relevance-Gated Cognition Projection"),
    ("1251.2", "Compact Cognitive Projection"),
    ("1251.3", "Immediate Trusted Action Feedback"),
    ("1251.4", "Lightweight Chat Launcher"),
    ("1251.5", "Provider Runtime Efficiency"),
    ("1251.6", "Dashboard API Prewarming"),
    ("1251.7", "Dashboard State Caching"),
    ("1251.8", "Static Dashboard Assets"),
)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _fixture_section(name: str, chars: int = 1200) -> dict[str, str]:
    return {"prompt_section": f"<{name}>" + ("x" * chars) + f"</{name}>"}


def response_time_contract(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    ordinary, ordinary_diag = build_compact_cognitive_projection(
        "Tell me what you think about this idea",
        action_projection={}, development_campaign={},
        cognitive=_fixture_section("cognition"),
        conversation_policy=_fixture_section("policy"),
        conversation_discourse=_fixture_section("discourse"),
        memory_retrieval=_fixture_section("memory"),
        natural_continuity=_fixture_section("continuity"),
        natural_follow_up=_fixture_section("followup"),
        governed_speech=_fixture_section("speech"),
        daily_companion=_fixture_section("companion"),
    )
    social, social_diag = build_compact_cognitive_projection(
        "Hi!", action_projection={}, development_campaign={},
        cognitive=_fixture_section("cognition"), conversation_policy=_fixture_section("policy"),
        conversation_discourse=_fixture_section("discourse"), memory_retrieval=_fixture_section("memory"),
        natural_continuity=_fixture_section("continuity"), natural_follow_up=_fixture_section("followup"),
        governed_speech=_fixture_section("speech"), daily_companion=_fixture_section("companion"),
    )
    metrics = provider_metrics_public({
        "load_duration_ns": 100_000_000, "prompt_eval_count": 1000,
        "prompt_eval_duration_ns": 2_000_000_000, "eval_count": 100,
        "eval_duration_ns": 2_000_000_000, "total_duration_ns": 4_100_000_000,
        "prompt": "private", "response": "private",
    })
    dashboard_source = (root / "conscious_agent/dashboard_layout.py").read_text(encoding="utf-8")
    synthetic_html = "<!doctype html><html><head><style>" + ("x" * 60_000) + "</style></head><body><script>(function () {" + ("y" * 5_000) + "</script></body></html>"
    optimized = optimize_dashboard_html_assets(synthetic_html)
    files = {
        "runtime": root / "conscious_agent/response_time_runtime.py",
        "launcher": root / "conscious_agent/chat_launcher.py",
        "dashboard_perf": root / "conscious_agent/dashboard_performance.py",
        "projection_cache": root / "conscious_agent/runtime_projection_cache.py",
        "css": root / "conscious_agent/static/dashboard.css",
        "js": root / "conscious_agent/static/dashboard.js",
        "local_model": root / "conscious_agent/local_model.py",
        "conversation_runtime": root / "conscious_agent/conversation_runtime.py",
        "dashboard": root / "conscious_agent/dashboard.py",
        "eidolon": root / "eidolon.py",
    }
    texts = {k: p.read_text(encoding="utf-8") if p.is_file() and p.suffix in {".py", ".js", ".css"} else "" for k,p in files.items()}
    checks = {
        "all_version_units_declared": len(VERSION_PLAN) == 9 and VERSION_PLAN[0][0] == "1251.0" and VERSION_PLAN[-1][0] == "1251.8",
        "compact_projection_bounded": len(ordinary) <= MAX_COMPACT_COGNITIVE_CHARS <= 3200,
        "social_projection_smaller": len(social) < len(ordinary) and social_diag["omitted_planning_by_relevance"],
        "ordinary_projection_under_800_estimated_tokens": ordinary_diag["estimated_projection_tokens"] <= 800,
        "social_projection_under_600_estimated_tokens": social_diag["estimated_projection_tokens"] <= 600,
        "dynamic_social_budget": generation_token_budget("Hi!", 350) == 96,
        "dynamic_budget_never_increases": generation_token_budget("Explain this in detail", 80) <= 80,
        "provider_metrics_content_free": metrics.get("generation_tokens_per_second") == 50.0 and "prompt" not in metrics and "response" not in metrics,
        "trusted_action_feedback_denies_execution": "Nothing has executed or been approved yet" in trusted_action_acknowledgement({"grounding":{"capability_id":"diagnostics"}}),
        "lightweight_launcher_present": "from main import" not in texts["launcher"] and "chat_launcher.py" in (root / "eidolon.py").read_text(encoding="utf-8"),
        "provider_session_reuse_present": "_shared_http_session" in texts["local_model"] and "last_metrics" in texts["local_model"],
        "api_prewarm_present": "prewarm_api_runtime_async" in texts["dashboard"],
        "status_cache_present": "cached_read_only_projection" in (root / "conscious_agent/api_server.py").read_text(encoding="utf-8"),
        "static_assets_present": files["css"].is_file() and files["js"].is_file() and files["css"].stat().st_size > 10_000,
        "served_html_externalizes_assets": len(optimized) < len(synthetic_html) - 50_000 and "/assets/dashboard.css" in optimized and "/assets/dashboard.js" in optimized,
        "frozen_shell_preserved": "def render_dashboard_layout" in dashboard_source,
        "action_claim_guard_preserved": "action_response_guarded" in texts["conversation_runtime"] and "replace" in texts["conversation_runtime"],
    }
    passed = sum(bool(v) for v in checks.values())
    result = {
        "ok": passed == len(checks), "status": "response_time_efficiency_ready" if passed == len(checks) else "response_time_efficiency_blocked",
        "contract_version": CONTRACT_VERSION, "milestone_name": MILESTONE_NAME,
        "versions": [{"version":v,"title":t} for v,t in VERSION_PLAN], "checks": checks,
        "passed": passed, "total": len(checks),
        "ordinary_projection_chars": len(ordinary), "ordinary_projection_estimated_tokens": ordinary_diag["estimated_projection_tokens"],
        "social_projection_chars": len(social), "social_projection_estimated_tokens": social_diag["estimated_projection_tokens"],
        "provider_metrics": metrics, "read_only": True, "content_free": True,
        **AUTHORITY_FLAGS,
    }
    result["contract_digest"] = _digest(result)
    return result


__all__ = ["CONTRACT_VERSION", "MILESTONE_NAME", "VERSION_PLAN", "response_time_contract"]
