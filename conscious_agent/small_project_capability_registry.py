from __future__ import annotations

"""Shared capability registry for supervised small-project implementation.

v1205.0-v1205.2 consolidates project-kind routing metadata without widening
execution or authority. Capability entries contain no private request text,
paths, provider payloads, or generated source.
"""

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import _digest

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1205.8"


@dataclass(frozen=True)
class SmallProjectCapability:
    capability_id: str
    project_kinds: tuple[str, ...]
    coordinator: str
    preview_required: bool
    validation_adapters: tuple[str, ...]
    project_tests_supported: bool
    selected_project_supported: bool

    def public_record(self) -> dict[str, Any]:
        record = {
            "capability_id": self.capability_id,
            "project_kinds": list(self.project_kinds),
            "coordinator": self.coordinator,
            "preview_required": self.preview_required,
            "validation_adapters": list(self.validation_adapters),
            "project_tests_supported": self.project_tests_supported,
            "selected_project_supported": self.selected_project_supported,
            "authority": "supervised_external_workspace_only",
            "authority_granted": False,
            "apply_authorized": False,
            "repair_authorized": False,
            "release_authorized": False,
        }
        record["capability_digest"] = _digest(record)
        return record


_CAPABILITIES = (
    SmallProjectCapability(
        capability_id="small_website",
        project_kinds=("new_small_web_project", "static_web_project", "javascript_or_web_project", "empty_project"),
        coordinator="small_website_implementation_checkpoint",
        preview_required=True,
        validation_adapters=("browser_document", "javascript_syntax"),
        project_tests_supported=True,
        selected_project_supported=True,
    ),
    SmallProjectCapability(
        capability_id="javascript_tool",
        project_kinds=("new_javascript_tool_project", "javascript_tool_project"),
        coordinator="javascript_tool_implementation_foundations",
        preview_required=False,
        validation_adapters=("javascript_syntax", "node_cli_smoke"),
        project_tests_supported=True,
        selected_project_supported=True,
    ),
    SmallProjectCapability(
        capability_id="python_cli",
        project_kinds=("new_python_cli_project", "python_project"),
        coordinator="python_cli_implementation_foundations",
        preview_required=False,
        validation_adapters=("python_syntax", "python_cli_smoke"),
        project_tests_supported=True,
        selected_project_supported=True,
    ),
)

_BY_KIND = {kind: capability for capability in _CAPABILITIES for kind in capability.project_kinds}
_BY_ID = {capability.capability_id: capability for capability in _CAPABILITIES}


def capability_for_project_kind(project_kind: str) -> SmallProjectCapability | None:
    return _BY_KIND.get(str(project_kind or "").strip())


def capability_by_id(capability_id: str) -> SmallProjectCapability | None:
    return _BY_ID.get(str(capability_id or "").strip())


def list_small_project_capabilities() -> dict[str, Any]:
    rows = [capability.public_record() for capability in _CAPABILITIES]
    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "small_project_capability_registry_ready",
        "capability_count": len(rows),
        "capabilities": rows,
        "supported_project_kinds": sorted(_BY_KIND),
        "unsupported_behavior": "explicit_limitation_state",
        "private_request_included": False,
        "private_path_included": False,
        "private_content_included": False,
        "authority_granted": False,
    }
    result["registry_digest"] = _digest(result)
    return result


def registry_digest() -> str:
    return str(list_small_project_capabilities()["registry_digest"])


def validate_registry(entries: Iterable[Mapping[str, Any]] | None = None) -> bool:
    rows = list(entries) if entries is not None else list_small_project_capabilities()["capabilities"]
    ids: set[str] = set()
    kinds: set[str] = set()
    for row in rows:
        capability_id = str(row.get("capability_id") or "")
        project_kinds = [str(value or "") for value in row.get("project_kinds") or []]
        if not capability_id or capability_id in ids or not project_kinds:
            return False
        if any(not kind or kind in kinds for kind in project_kinds):
            return False
        ids.add(capability_id)
        kinds.update(project_kinds)
    return True
