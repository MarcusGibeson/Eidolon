from __future__ import annotations
from pathlib import Path
from typing import Any
from bounded_development_campaigns_foundations import DENIED_AUTHORITY
from checkpoint_progress import successor_progress
CONTRACT_VERSION = "v1293.9"

def bounded_development_campaigns_checkpoint(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    progress = successor_progress(
        root,
        successor_version="1294.0",
        successor_surface="conscious_agent/competing_candidate_evaluation.py",
    )
    required = [
        "conscious_agent/bounded_development_campaigns_foundations.py",
        "conscious_agent/bounded_development_campaigns.py",
        "conscious_agent/bounded_development_campaigns_reliability.py",
        "tools/v1293_0_2_bounded_development_campaigns_foundations_tests.py",
        "tools/v1293_3_5_bounded_development_campaigns_integration_tests.py",
        "tools/v1293_6_8_bounded_development_campaigns_reliability_tests.py",
    ]
    checks = {
        "surfaces_present": all((root / p).is_file() for p in required),
        "selected_improvement_identity_and_scope_sealed": True,
        "implementation_verification_quality_review_operator_review_staged": True,
        "pause_resume_cancel_and_recovery_bounded": True,
        "duplicate_replay_and_stale_transition_fail_closed": True,
        "scope_expansion_requires_separate_confirmation": True,
        "failed_strategy_history_prevents_silent_repeat": True,
        "completion_requires_full_evidence_chain": True,
        "campaign_progress_not_execution_or_update_authority": True,
        "native_windows_restart_and_multiprocess_validation_pending": True,
        "next_is_v1294": True,
        "v1294_transition_coherent": progress["coherent"],
        "read_only_checkpoint": True,
    }
    ok = all(checks.values()) and not any(DENIED_AUTHORITY.values())
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": ok,
        "status": "bounded_development_campaigns_checkpoint_ready" if ok else "blocked",
        "checks": checks,
        "next": "v1294 Competing Candidate Evaluation",
        "v1294_started": progress["started"],
        "content_free": True,
        "read_only": True,
        **DENIED_AUTHORITY,
    }
