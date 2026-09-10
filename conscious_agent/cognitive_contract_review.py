from __future__ import annotations

"""v1150.0 executable review of cognitive contracts and ordinary conversation reachability.

The review is static and content-free. It inspects Python imports, lazy service
registrations, checkpoint builders, and direct calls without importing provider
clients or reading runtime data. The result is intended to be regression-tested
and consumed by later cognitive-integration work.
"""

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

CONTRACT_VERSION = "v1150.0"
ORDINARY_CONVERSATION_ROOTS = (
    "conscious_agent.chat",
    "conscious_agent.conversation_runtime",
    "conscious_agent.conversation_context",
    "conscious_agent.dashboard_chat_console",
)
COGNITIVE_TOKENS = (
    "attention", "belief", "cognit", "concern", "continuity", "correction",
    "curiosity", "deliberat", "desire", "goal", "inquiry", "memory", "mood",
    "motivation", "planning", "reflection", "reflective", "relationship",
    "self_model", "thought", "workload", "world_model",
)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _source_root(value: str | Path | None = None) -> Path:
    return Path(value or Path(__file__).resolve().parents[1]).expanduser().resolve()


def _module_name(path: Path) -> str:
    return f"conscious_agent.{path.stem}"


def _literal_string(node: ast.AST) -> str:
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError):
        return ""
    return str(value) if isinstance(value, str) else ""


def _contract_version(tree: ast.Module) -> str:
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(target, ast.Name) and target.id == "CONTRACT_VERSION" for target in targets):
            return _literal_string(node.value)
    return ""


def _version_number(value: str) -> tuple[int, int]:
    token = str(value or "").strip().lower().lstrip("v")
    try:
        major, minor = token.split(".", 1)
        return int(major), int("".join(ch for ch in minor if ch.isdigit()) or 0)
    except (ValueError, AttributeError):
        return (0, 0)


def _normalize_import(module: str, available: set[str]) -> str:
    token = str(module or "").strip()
    if not token:
        return ""
    if token.startswith("conscious_agent."):
        return token if token in available else ""
    candidate = f"conscious_agent.{token.split('.', 1)[0]}"
    return candidate if candidate in available else ""


def _parse_modules(source: Path) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    package = source / "conscious_agent"
    paths = sorted(package.glob("*.py"))
    available = {_module_name(path) for path in paths}
    modules: dict[str, dict[str, Any]] = {}
    edges: dict[str, list[dict[str, Any]]] = {}
    for path in paths:
        name = _module_name(path)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as error:
            modules[name] = {
                "module": name,
                "relative_path": path.relative_to(source).as_posix(),
                "parse_error": type(error).__name__,
                "contract_version": "",
                "checkpoint_builders": [],
                "direct_calls": [],
            }
            edges[name] = []
            continue
        imports: list[dict[str, Any]] = []
        calls: list[dict[str, Any]] = []
        builders: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = _normalize_import(alias.name, available)
                    if target:
                        imports.append({"target": target, "line": node.lineno, "kind": "import"})
            elif isinstance(node, ast.ImportFrom):
                target = _normalize_import(node.module or "", available)
                if target:
                    imports.append({"target": target, "line": node.lineno, "kind": "from"})
            elif isinstance(node, ast.Call):
                call_name = ""
                if isinstance(node.func, ast.Name):
                    call_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    call_name = node.func.attr
                if call_name:
                    calls.append({"name": call_name, "line": node.lineno})
                if call_name == "install_lazy_callables" and len(node.args) >= 2:
                    target = _normalize_import(_literal_string(node.args[1]), available)
                    if target:
                        imports.append({"target": target, "line": node.lineno, "kind": "lazy_service"})
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("build_") and "checkpoint" in node.name:
                    builders.append(node.name)
        deduped = {(row["target"], row["line"], row["kind"]): row for row in imports}
        modules[name] = {
            "module": name,
            "relative_path": path.relative_to(source).as_posix(),
            "parse_error": "",
            "contract_version": _contract_version(tree),
            "checkpoint_builders": sorted(set(builders)),
            "direct_calls": calls,
        }
        edges[name] = sorted(deduped.values(), key=lambda row: (row["target"], row["line"], row["kind"]))
    return modules, edges


def _reachable(roots: Iterable[str], edges: dict[str, list[dict[str, Any]]]) -> set[str]:
    pending = [root for root in roots if root in edges]
    seen: set[str] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(row["target"] for row in edges.get(current, ()) if row["target"] not in seen)
    return seen


def _is_cognitive_capability(module: str, row: dict[str, Any]) -> bool:
    stem = module.rsplit(".", 1)[-1]
    version = _version_number(row.get("contract_version", ""))
    return version >= (1108, 0) or any(token in stem for token in COGNITIVE_TOKENS)


def _call_evidence(module: str, modules: dict[str, dict[str, Any]], names: set[str]) -> list[dict[str, Any]]:
    row = modules.get(module) or {}
    return [
        {"module": module, "relative_path": row.get("relative_path", ""), **call}
        for call in row.get("direct_calls", ())
        if call.get("name") in names
    ]


def build_cognitive_contract_review(source_root: str | Path | None = None) -> dict[str, Any]:
    """Return deterministic, executable findings about current cognitive integration."""

    source = _source_root(source_root)
    modules, edges = _parse_modules(source)
    checkpoint_roots = sorted(
        module for module, row in modules.items()
        if row.get("checkpoint_builders") and module != "conscious_agent.architecture_checkpoint_dispatch"
    )
    ordinary = _reachable(ORDINARY_CONVERSATION_ROOTS, edges)
    checkpoint_reachable = _reachable(checkpoint_roots, edges)
    capabilities = sorted(
        module for module, row in modules.items()
        if _is_cognitive_capability(module, row) and "checkpoint" not in module.rsplit(".", 1)[-1]
    )
    classifications: list[dict[str, Any]] = []
    for module in capabilities:
        row = modules[module]
        if module in ordinary:
            state = "ordinary_conversation_connected"
        elif module in checkpoint_reachable:
            state = "checkpoint_only"
        else:
            state = "not_reachable_from_reviewed_surfaces"
        classifications.append({
            "module": module,
            "relative_path": row["relative_path"],
            "contract_version": row["contract_version"],
            "integration_state": state,
        })

    try:
        from checkpoint_registry import checkpoint_descriptors, inspect_checkpoint_registry
    except ImportError:
        from checkpoint_registry import checkpoint_descriptors, inspect_checkpoint_registry
    registered = tuple(checkpoint_descriptors(source_root=source))
    registry = inspect_checkpoint_registry(source_root=source)
    discovered_builder_count = sum(len(modules[module]["checkpoint_builders"]) for module in checkpoint_roots)

    findings: list[dict[str, Any]] = []
    resolved_findings: list[dict[str, Any]] = []
    registry_healthy = (
        registry.get("contract_version") == "v1150.2"
        and not registry.get("duplicate_checkpoint_ids")
        and not registry.get("duplicate_builder_targets")
        and registry.get("all_compatibility_targets_available") is True
        and len(registered) >= 150
    )
    if registry_healthy:
        resolved_findings.append({
            "finding_id": "checkpoint-registry-incomplete",
            "severity": "high",
            "status": "resolved_in_v1150.2",
            "evidence": {
                "registered_current_checkpoint_count": len(registered),
                "all_source_checkpoint_builder_count": discovered_builder_count,
                "historical_or_noncurrent_builder_count": max(0, discovered_builder_count - len(registered)),
            },
            "resolution": "source_discovered_checkpoint_registry",
        })
    else:
        findings.append({
            "finding_id": "checkpoint-registry-incomplete",
            "severity": "high",
            "status": "open",
            "evidence": {
                "registered_descriptor_count": len(registered),
                "discovered_checkpoint_builder_count": discovered_builder_count,
                "duplicate_checkpoint_ids": list(registry.get("duplicate_checkpoint_ids") or []),
                "duplicate_builder_targets": list(registry.get("duplicate_builder_targets") or []),
            },
            "required_action": "source_discovered_checkpoint_registry",
        })

    v1145_modules = (
        "conscious_agent.conversation_cognition_communication_arbitration",
        "conscious_agent.conversation_cognition_bounded_generation",
        "conscious_agent.conversation_cognition_cross_cycle_continuity",
    )
    disconnected_v1145 = [module for module in v1145_modules if module not in ordinary and module in modules]
    backbone_connected = "conscious_agent.conversation_cognitive_backbone" in ordinary
    if disconnected_v1145 and not backbone_connected:
        findings.append({
            "finding_id": "v1145-contracts-not-in-ordinary-turn-path",
            "severity": "high",
            "status": "open",
            "evidence": {"modules": disconnected_v1145, "ordinary_roots": list(ORDINARY_CONVERSATION_ROOTS)},
            "required_action": "connect_shared_cognitive_context_to_conversation_runtime",
        })
    elif backbone_connected:
        resolved_findings.append({
            "finding_id": "v1145-contracts-not-in-ordinary-turn-path",
            "severity": "high",
            "status": "resolved_in_v1150.3",
            "evidence": {"backbone_module": "conscious_agent.conversation_cognitive_backbone", "ordinary_roots": list(ORDINARY_CONVERSATION_ROOTS)},
            "resolution": "bounded_cognitive_context_on_authoritative_runtime",
        })

    reflection_calls = _call_evidence(
        "conscious_agent.chat", modules, {"generate_inner_thought", "reflect_on_thought", "store_memory"}
    ) + _call_evidence(
        "conscious_agent.dashboard_chat_console", modules, {"generate_inner_thought", "reflect_on_thought", "store_memory_batch"}
    )
    runtime_reflection_calls = _call_evidence(
        "conscious_agent.conversation_runtime", modules, {"generate_inner_thought", "reflect_on_thought", "record_turn_completion", "record_turn_completion_safely"}
    )
    if reflection_calls and not runtime_reflection_calls:
        findings.append({
            "finding_id": "post-reply-reflection-split-from-authoritative-runtime",
            "severity": "medium",
            "status": "open",
            "evidence": {"surface_calls": reflection_calls, "conversation_runtime_calls": runtime_reflection_calls},
            "required_action": "move_reflection_outcomes_behind_shared_turn_lifecycle",
        })
    elif runtime_reflection_calls:
        resolved_findings.append({
            "finding_id": "post-reply-reflection-split-from-authoritative-runtime",
            "severity": "medium",
            "status": "resolved_in_v1150.4",
            "evidence": {"conversation_runtime_calls": runtime_reflection_calls},
            "resolution": "idempotent_authoritative_turn_completion",
        })

    state_counts = {
        state: sum(row["integration_state"] == state for row in classifications)
        for state in ("ordinary_conversation_connected", "checkpoint_only", "not_reachable_from_reviewed_surfaces")
    }
    report = {
        "contract_version": CONTRACT_VERSION,
        "review_id": "cognitive-contract-review:v1150.0",
        "ok": not any(row["severity"] == "high" and row["status"] == "open" for row in findings),
        "status": "integration_gaps_found" if findings else "connected",
        "ordinary_conversation_roots": list(ORDINARY_CONVERSATION_ROOTS),
        "ordinary_reachable_module_count": len(ordinary),
        "checkpoint_builder_module_count": len(checkpoint_roots),
        "checkpoint_builder_count": discovered_builder_count,
        "registered_checkpoint_count": len(registered),
        "historical_or_noncurrent_checkpoint_builder_count": max(0, discovered_builder_count - len(registered)),
        "cognitive_capability_count": len(classifications),
        "integration_state_counts": state_counts,
        "capabilities": classifications,
        "findings": findings,
        "finding_count": len(findings),
        "resolved_findings": resolved_findings,
        "resolved_finding_count": len(resolved_findings),
        "provider_contacted": False,
        "runtime_data_read": False,
        "runtime_mutated": False,
        "source_modified": False,
        "private_content_included": False,
        "content_free": True,
    }
    report["structural_digest"] = _digest({key: value for key, value in report.items() if key != "structural_digest"})
    return report
