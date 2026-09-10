from __future__ import annotations

"""Read-only v1253.9.1 pre-Codex runtime coherence contract."""

import hashlib
import json
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "v1253.9.1"
AUTHORITY_FLAGS = {
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "provider_contact_authorized": False,
    "tool_execution_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "approval_granted": False,
    "independent_authority_granted": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def pre_codex_runtime_coherence_contract(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    launcher = (root / "conscious_agent/chat_launcher.py").read_text(encoding="utf-8")
    legacy_chat = (root / "conscious_agent/chat.py").read_text(encoding="utf-8")
    maintenance = (root / "conscious_agent/bounded_internal_maintenance.py").read_text(encoding="utf-8")
    response_time = (root / "conscious_agent/response_time_runtime.py").read_text(encoding="utf-8")
    benchmark = (root / "conscious_agent/runtime_efficiency_benchmark.py").read_text(encoding="utf-8")
    authority = (root / "conscious_agent/release_authority.py").read_text(encoding="utf-8")
    desktop = (root / "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md").read_text(encoding="utf-8")
    checks = {
        "terminal_hidden_second_provider_removed": all(
            token not in surface
            for surface in (launcher, legacy_chat)
            for token in ("_post_reply_reflection", "generate_inner_thought", 'brain_mode="local_ai"')
        ),
        "terminal_resumes_pending_housekeeping": "resume_pending_internal_maintenance" in launcher,
        "maintenance_exact_lifecycle": all(token in maintenance for token in ('"state": "pending"', 'row["state"] = "running"', 'row["state"] = "pending"', "resume_pending_internal_maintenance")),
        "maintenance_global_coalescing": "global_housekeeping_coalesced" in maintenance and "GLOBAL_COOLDOWN_SECONDS" in maintenance,
        "decision_support_relevance_expanded": all(token in response_time for token in ("decide", "trade[ -]?offs?", "what would you", "think through")),
        "benchmark_scoped_temp_cleanup": "TemporaryDirectory" in benchmark and "mkdtemp" not in benchmark,
        "benchmark_first_message_metrics": all(token in benchmark for token in ("first_message_pre_provider_ms", "first_message_next_input_ready_ms", "first_message_provider_request_count")),
        "benchmark_fresh_and_established_startup": all(token in benchmark for token in ("terminal_cold_start_fresh_data_seconds", "terminal_cold_start_established_runtime_seconds")),
        "benchmark_incremental_import_named": "conversation_runtime_incremental_import_seconds" in benchmark,
        "same_host_baseline_module_present": (root / "conscious_agent/performance_baseline.py").is_file(),
        "mixed_load_contention_benchmark_present": (root / "conscious_agent/runtime_contention_benchmark.py").is_file(),
        "schema_lineage_explicit": "RELEASE_AUTHORITY_SCHEMA_VERSION = CONTRACT_VERSION" in authority,
        "desktop_alpha_marked_historical": "HISTORICAL / ARCHIVAL DOCUMENT" in desktop,
        "authority_denied": not any(AUTHORITY_FLAGS.values()),
    }
    result = {
        "ok": all(checks.values()),
        "status": "pre_codex_runtime_coherence_repair_ready" if all(checks.values()) else "pre_codex_runtime_coherence_repair_blocked",
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
        "read_only": True,
        "content_free": True,
        **AUTHORITY_FLAGS,
    }
    result["contract_digest"] = _digest(result)
    return result


__all__ = ["CONTRACT_VERSION", "AUTHORITY_FLAGS", "pre_codex_runtime_coherence_contract"]
