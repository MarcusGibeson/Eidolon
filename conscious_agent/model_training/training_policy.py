from __future__ import annotations

"""Durable, operator-owned policy for runtime-only training evidence capture."""

from dataclasses import asdict, dataclass
from typing import Any, Mapping

try:
    from settings_manager import load_settings, validate_settings_patch, save_settings
except ImportError:
    from settings_manager import load_settings, validate_settings_patch, save_settings

CONTRACT_VERSION = "v2503.4.31"

SETTING_KEYS = {
    "training_capture_coding_repair_enabled",
    "training_capture_research_enabled",
    "training_capture_planning_enabled",
    "training_capture_tool_governance_enabled",
    "training_capture_conversation_enabled",
    "training_auto_sanitize_enabled",
}


@dataclass(frozen=True)
class TrainingEvidenceCapturePolicy:
    coding_repair_enabled: bool = True
    research_enabled: bool = True
    planning_enabled: bool = True
    tool_governance_enabled: bool = True
    conversation_enabled: bool = False
    auto_sanitize_enabled: bool = True
    auto_approve_enabled: bool = False
    automatic_dataset_export_enabled: bool = False
    model_training_authorized: bool = False
    model_promotion_authorized: bool = False

    def capture_enabled(self, capability: str) -> bool:
        key = str(capability or "").strip().lower()
        return {
            "coding": self.coding_repair_enabled,
            "repair": self.coding_repair_enabled,
            "software_development": self.coding_repair_enabled,
            "software_repair": self.coding_repair_enabled,
            "research": self.research_enabled,
            "research_synthesis": self.research_enabled,
            "planning": self.planning_enabled,
            "tool_use": self.tool_governance_enabled,
            "governance": self.tool_governance_enabled,
            "conversation": self.conversation_enabled,
        }.get(key, False)

    def public_record(self) -> dict[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "migration_behavior": "missing_policy_keys_persist_safe_capture_defaults",
            **asdict(self),
        }


def resolve_training_evidence_capture_policy(settings: Mapping[str, Any] | None = None) -> TrainingEvidenceCapturePolicy:
    row = dict(settings or load_settings())
    return TrainingEvidenceCapturePolicy(
        coding_repair_enabled=bool(row.get("training_capture_coding_repair_enabled", True)),
        research_enabled=bool(row.get("training_capture_research_enabled", True)),
        planning_enabled=bool(row.get("training_capture_planning_enabled", True)),
        tool_governance_enabled=bool(row.get("training_capture_tool_governance_enabled", True)),
        conversation_enabled=bool(row.get("training_capture_conversation_enabled", False)),
        auto_sanitize_enabled=bool(row.get("training_auto_sanitize_enabled", True)),
    )


def update_training_evidence_capture_policy(patch: Mapping[str, Any]) -> TrainingEvidenceCapturePolicy:
    updated = validate_settings_patch(dict(patch), allowed_keys=SETTING_KEYS)
    save_settings(updated)
    return resolve_training_evidence_capture_policy(updated)
