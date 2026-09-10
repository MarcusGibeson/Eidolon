from __future__ import annotations

from pathlib import Path

from checkpoint_registry import build_read_only_checkpoint_report
from unified_conversation_action_foundations import CONTRACT_VERSION as F
from unified_conversation_action import CONTRACT_VERSION as I
from unified_conversation_action_reliability import CONTRACT_VERSION as R, inspect_unified_conversation_action_health

CONTRACT_VERSION = "v1287.9"


def build_unified_conversation_action_checkpoint(*, source_root=None):
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    health = inspect_unified_conversation_action_health(source_root=root)
    checks = {
        "foundations_current": F == "v1287.2",
        "integration_current": I == "v1287.5",
        "reliability_current": R == "v1287.8",
        "health": health.get("ok") is True,
        "v1259_lineage": (root / "conscious_agent/conversational_command_integration.py").is_file(),
        "ordinary_chat_lineage": (root / "conscious_agent/ordinary_chat_development_campaign.py").is_file(),
        "operator_experience_lineage": (root / "conscious_agent/operator_experience.py").is_file(),
        "long_session_lineage": (root / "conscious_agent/long_running_work_sessions.py").is_file(),
    }
    return build_read_only_checkpoint_report(
        version="1287.9",
        status="unified_conversation_action_checkpoint_ready",
        checks=checks,
        source_root=root,
        details={
            "next_bounded_unit": "v1288 Provider-Aware Performance",
            "v1288_started": False,
            "companionship_discussion_questions_actions_progress_corrections_cancellation_supported": True,
            "ordinary_chat_and_supervised_development_reused": True,
            "generic_authorization_never_exact": True,
            "progress_reporting_read_only": True,
            "technical_execution_not_inferred_from_language": True,
            "parallel_conversation_system_created": False,
            "parallel_execution_engine_created": False,
            "provider_contacted": False,
            "commands_executed": False,
            "project_modified": False,
            "release_authorized": False,
            "independent_authority_granted": False,
            "native_windows_multi_process_validation": "desktop_review_required",
        },
    )


__all__ = ["CONTRACT_VERSION", "build_unified_conversation_action_checkpoint"]
