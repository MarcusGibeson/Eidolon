from __future__ import annotations

"""v1266.0-v1266.2 foundations for intelligent self-candidate test selection.

Consumes only a sealed v1265 isolated self-modification candidate and its
source-only disposable workspace.  The selector inventories tests, derives an
affected surface from changed paths plus bounded Python import relationships,
and produces a content-minimized test plan.  It never executes tests, contacts
a provider, mutates source, or grants application/self-update authority.
"""

import ast
import hashlib
import json
import os
import re
import tempfile
from collections import defaultdict, deque
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from isolated_self_modification_foundations import (
    SELF_MODIFICATION_DENIED_AUTHORITY,
    _digest,
    _is_link_like,
    _runtime_root,
    load_self_modification,
    source_only_manifest,
)
from isolated_self_modification_reliability import validate_self_modification_candidate
from ordinary_chat_development_campaign import _proposal_lock

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1266.2"
MAX_TEST_FILES = 2400
MAX_SOURCE_FILES_FOR_GRAPH = 5000
MAX_PARSE_BYTES = 1024 * 1024
MAX_SELECTED_TESTS = 96
MAX_GRAPH_DEPTH = 2
MAX_RUNTIME_RECORD_BYTES = 4 * 1024 * 1024

TEST_SELECTION_DENIED_AUTHORITY = {
    **SELF_MODIFICATION_DENIED_AUTHORITY,
    "test_selection_authorized": True,
    "test_execution_authorized": False,
    "repair_authorized": False,
}

CORE_REGRESSION_HINTS: dict[str, tuple[str, ...]] = {
    "release_control": ("v1250_3_release_metadata", "v1250_4_checkpoint_registry"),
    "privacy_security": ("v1247_9", "privacy", "package_integrity"),
    "conversation": ("v1259_", "ordinary_chat", "conversation"),
    "coding_pipeline": ("v1260_", "v1254_", "isolated_coding"),
    "self_modification": ("v1265_", "isolated_self_modification", "v1264_9", "v1255_9", "v1247_9"),
    "inspection_planning": ("v1261_", "v1262_", "v1263_", "v1264_"),
    "operator_surface": ("dashboard", "api_server"),
}


def _record_dir(runtime_root: str | Path | None) -> Path:
    return _runtime_root(runtime_root) / "intelligent_test_selection" / "records"


def _record_path(selection_id: str, runtime_root: str | Path | None) -> Path:
    if not re.fullmatch(r"testsel_[a-f0-9]{24}", str(selection_id or "")):
        raise ValueError("invalid_test_selection_id")
    return _record_dir(runtime_root) / f"{selection_id}.json"


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    data = (json.dumps(dict(value), indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")
    if len(data) > MAX_RUNTIME_RECORD_BYTES:
        raise ValueError("test_selection_record_too_large")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent, suffix=".tmp") as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno()); tmp = Path(handle.name)
        os.replace(tmp, path); tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if path.stat().st_size > MAX_RUNTIME_RECORD_BYTES:
        raise ValueError("test_selection_record_too_large")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("test_selection_record_invalid")
    return value


def _record_digest(record: Mapping[str, Any]) -> str:
    return _digest({k: v for k, v in record.items() if k not in {"record_digest", "operation_status"}})


def _module_name(rel: str) -> str | None:
    pure = PurePosixPath(rel)
    if pure.suffix.casefold() != ".py":
        return None
    parts = list(pure.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return None
    return ".".join(parts)


def _import_names(path: Path) -> set[str]:
    try:
        if path.stat().st_size > MAX_PARSE_BYTES:
            return set()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
    except (OSError, UnicodeError, SyntaxError):
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module)
    return names


def _matches_module(imported: str, module: str) -> bool:
    return imported == module or imported.endswith("." + module) or module.endswith("." + imported)


def _classify_surfaces(changed_paths: Iterable[str]) -> list[str]:
    surfaces: set[str] = set()
    for rel in changed_paths:
        low = rel.casefold()
        if low.startswith("conscious_agent/"):
            surfaces.add("python_runtime")
        if low.startswith("tools/") or low.startswith("tests/"):
            surfaces.add("test_infrastructure")
        if low.startswith("docs/") or low.startswith("readme") or low.endswith(".md"):
            surfaces.add("documentation")
        if any(token in low for token in ("release_authority", "release_metadata", "checkpoint_registry")):
            surfaces.add("release_control")
        if any(token in low for token in ("package_integrity", "privacy", "secret", "security")):
            surfaces.add("privacy_security")
        if any(token in low for token in ("conversation", "ordinary_chat", "natural_language", "speech_act")):
            surfaces.add("conversation")
        if any(token in low for token in ("isolated_coding", "development_campaign", "coding_alpha")):
            surfaces.add("coding_pipeline")
        if any(token in low for token in ("isolated_self_modification", "self_modification")):
            surfaces.add("self_modification")
        if any(token in low for token in ("evidence_based", "backlog", "priority_selection", "alternative_planning")):
            surfaces.add("inspection_planning")
        if any(token in low for token in ("dashboard", "api_server")):
            surfaces.add("operator_surface")
    if not surfaces:
        surfaces.add("unclassified")
    return sorted(surfaces)


def _is_test_path(rel: str) -> bool:
    pure = PurePosixPath(rel)
    name = pure.name.casefold()
    return (
        (pure.parts and pure.parts[0].casefold() in {"tools", "tests"})
        and (name.endswith("_tests.py") or (name.startswith("test_") and name.endswith(".py"))
             or name.endswith(".test.js") or name.endswith(".test.mjs") or name.endswith(".spec.js"))
    )


def _test_inventory(workspace: Path) -> list[str]:
    rows: list[str] = []
    folded: set[str] = set()
    for base in (workspace / "tools", workspace / "tests"):
        if not base.exists():
            continue
        for path in sorted(base.rglob("*"), key=lambda p: p.as_posix().casefold()):
            if _is_link_like(path):
                raise ValueError("test_selection_link_or_reparse_rejected")
            if not path.is_file():
                continue
            rel = path.relative_to(workspace).as_posix()
            if not _is_test_path(rel):
                continue
            key = rel.casefold()
            if key in folded:
                raise ValueError("test_selection_casefold_collision")
            folded.add(key); rows.append(rel)
            if len(rows) > MAX_TEST_FILES:
                raise ValueError("test_inventory_bound_exceeded")
    return rows


def _source_import_graph(workspace: Path) -> tuple[dict[str, set[str]], dict[str, str]]:
    imports: dict[str, set[str]] = {}
    module_to_path: dict[str, str] = {}
    count = 0
    for path in sorted((workspace / "conscious_agent").rglob("*.py"), key=lambda p: p.as_posix().casefold()) if (workspace / "conscious_agent").exists() else []:
        if _is_link_like(path):
            raise ValueError("test_selection_link_or_reparse_rejected")
        if not path.is_file():
            continue
        rel = path.relative_to(workspace).as_posix(); module = _module_name(rel)
        if module:
            module_to_path[module] = rel; imports[module] = _import_names(path)
        count += 1
        if count > MAX_SOURCE_FILES_FOR_GRAPH:
            raise ValueError("source_import_graph_bound_exceeded")
    return imports, module_to_path


def _affected_modules(changed_paths: list[str], imports: Mapping[str, set[str]]) -> tuple[set[str], dict[str, int]]:
    changed_modules = {m for m in (_module_name(rel) for rel in changed_paths) if m}
    # Also expose the final segment because many tests import from a sys.path-injected conscious_agent directory.
    seeds = set(changed_modules)
    seeds.update(m.split(".")[-1] for m in changed_modules)
    reverse: dict[str, set[str]] = defaultdict(set)
    for module, names in imports.items():
        for imported in names:
            reverse[imported].add(module)
    affected: set[str] = set(changed_modules)
    depth_by: dict[str, int] = {m: 0 for m in changed_modules}
    q: deque[tuple[str, int]] = deque((m, 0) for m in changed_modules)
    while q:
        current, depth = q.popleft()
        if depth >= MAX_GRAPH_DEPTH:
            continue
        for module, names in imports.items():
            if module in affected:
                continue
            if any(_matches_module(name, current) or _matches_module(name, current.split(".")[-1]) for name in names):
                affected.add(module); depth_by[module] = depth + 1; q.append((module, depth + 1))
    return affected | seeds, depth_by


def _select_tests(workspace: Path, changed_paths: list[str], surfaces: list[str], *, trusted_test_root: Path | None = None) -> tuple[list[dict[str, Any]], list[str], dict[str, int]]:
    test_root = trusted_test_root or workspace
    inventory = _test_inventory(test_root)
    imports, _ = _source_import_graph(workspace)
    affected_modules, depth_by = _affected_modules(changed_paths, imports)
    changed_tokens = {PurePosixPath(p).stem.casefold() for p in changed_paths}
    changed_tokens.update(token.removeprefix("test_").removesuffix("_tests") for token in list(changed_tokens))
    selected: dict[str, dict[str, Any]] = {}

    def add(rel: str, tier: str, reason: str, strength: int) -> None:
        old = selected.get(rel)
        row = {"relative_path": rel, "tier": tier, "reason_code": reason, "evidence_strength": strength, "content_exposed": False}
        if old is None or strength > int(old["evidence_strength"]):
            selected[rel] = row

    for rel in inventory:
        path = test_root / rel; low = rel.casefold(); stem = path.stem.casefold()
        names = _import_names(path) if path.suffix.casefold() == ".py" else set()
        if rel in changed_paths:
            add(rel, "focused", "changed_test_file", 100)
            continue
        if any(token and token in stem for token in changed_tokens):
            add(rel, "focused", "changed_path_name_match", 90)
        matching = [m for m in affected_modules if any(_matches_module(name, m) or _matches_module(name, m.split(".")[-1]) for name in names)]
        if matching:
            min_depth = min(depth_by.get(m, 0) for m in matching)
            add(rel, "focused" if min_depth <= 0 else "regression", "direct_import_of_changed_module" if min_depth <= 0 else "transitive_affected_module", 95 - min_depth * 15)

    for surface in surfaces:
        for hint in CORE_REGRESSION_HINTS.get(surface, ()):
            for rel in inventory:
                if hint.casefold() in rel.casefold():
                    add(rel, "regression", f"{surface}_regression_surface", 70)

    # A self-candidate with no precise match still needs bounded retained evidence.
    if not selected:
        for rel in inventory:
            if "v1265_9_isolated_self_modification_checkpoint" in rel.casefold():
                add(rel, "regression", "self_modification_checkpoint_fallback", 60)
            elif "v1247_9" in rel.casefold():
                add(rel, "regression", "privacy_checkpoint_fallback", 55)

    rows = sorted(selected.values(), key=lambda r: (-int(r["evidence_strength"]), r["relative_path"].casefold()))
    if len(rows) > MAX_SELECTED_TESTS:
        rows = rows[:MAX_SELECTED_TESTS]
    return rows, inventory, depth_by


def _semantic_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_operation_id": record.get("source_operation_id"),
        "source_result_digest": record.get("source_result_digest"),
        "candidate_manifest_digest": record.get("candidate_manifest_digest"),
        "changed_paths": record.get("changed_paths"),
        "affected_surfaces": record.get("affected_surfaces"),
        "selected_tests": record.get("selected_tests"),
        "test_inventory_digest": record.get("test_inventory_digest"),
        "candidate_source_manifest_digest": record.get("candidate_source_manifest_digest"),
        "selection_policy_version": record.get("selection_policy_version"),
        "test_ownership_integrity": record.get("test_ownership_integrity"),
        "supplemental_candidate_tests": record.get("supplemental_candidate_tests"),
    }


def validate_test_selection(record: Mapping[str, Any]) -> dict[str, Any]:
    digest_ok = bool(record.get("record_digest")) and record.get("record_digest") == _record_digest(record)
    selection_digest_ok = bool(record.get("selection_digest")) and record.get("selection_digest") == _digest(_semantic_payload(record))
    authority_ok = all(record.get(k) is v for k, v in TEST_SELECTION_DENIED_AUTHORITY.items())
    rows = list(record.get("selected_tests") or [])
    semantic_ok = (
        str(record.get("selection_id") or "").startswith("testsel_")
        and record.get("status") == "intelligent_test_selection_ready"
        and bool(record.get("source_result_digest"))
        and bool(record.get("candidate_manifest_digest"))
        and isinstance(record.get("changed_paths"), list)
        and len(rows) <= MAX_SELECTED_TESTS
        and all(isinstance(r, Mapping) and r.get("content_exposed") is False and r.get("tier") in {"focused", "regression"} for r in rows)
        and record.get("tests_executed") is False
        and record.get("test_ownership_integrity") == "preserved"
        and isinstance(record.get("supplemental_candidate_tests"), list)
    )
    ok = digest_ok and selection_digest_ok and authority_ok and semantic_ok
    return {"ok": ok, "status": "intelligent_test_selection_valid" if ok else "intelligent_test_selection_invalid", "record_digest_valid": digest_ok, "selection_digest_valid": selection_digest_ok, "authority_contained": authority_ok, "semantic_valid": semantic_ok}


def prepare_intelligent_test_selection(
    source_operation_id: str,
    source_root: str | Path,
    *,
    self_modification_runtime_root: str | Path | None,
    runtime_root: str | Path | None,
) -> dict[str, Any]:
    validation = validate_self_modification_candidate(source_operation_id, source_root, runtime_root=self_modification_runtime_root)
    if not validation.get("ok"):
        raise ValueError("invalid_v1265_self_modification_candidate")
    source_record = load_self_modification(source_operation_id, runtime_root=self_modification_runtime_root)
    if source_record.get("phase") != "sealed" or source_record.get("status") != "isolated_self_modification_candidate_ready":
        raise ValueError("sealed_v1265_candidate_required")
    result = dict(source_record.get("result") or {})
    changed_paths = sorted(str(row.get("relative_path") or "") for row in result.get("changed_files") or [] if row.get("relative_path"))
    if not changed_paths:
        raise ValueError("self_candidate_has_no_changed_paths")
    changed_rows = list(result.get("changed_files") or [])
    modified_trusted_tests = [str(row.get("relative_path") or "") for row in changed_rows if _is_test_path(str(row.get("relative_path") or "")) and str(row.get("action") or "") in {"modify", "delete"}]
    if modified_trusted_tests:
        raise ValueError("candidate_modified_or_deleted_trusted_test_rejected")
    supplemental_candidate_tests = sorted(str(row.get("relative_path") or "") for row in changed_rows if _is_test_path(str(row.get("relative_path") or "")) and str(row.get("action") or "") == "create")
    workspace = Path(str(source_record.get("workspace_path") or "")).expanduser().resolve(strict=True)
    candidate_manifest = source_only_manifest(workspace)
    if candidate_manifest["source_manifest_digest"] != result.get("candidate_manifest_digest"):
        raise ValueError("self_candidate_workspace_manifest_mismatch")
    source_result_digest = str(source_record.get("result_digest") or "")
    selection_id = "testsel_" + hashlib.sha256(f"{source_operation_id}:{source_result_digest}:{candidate_manifest['source_manifest_digest']}".encode()).hexdigest()[:24]
    record_path = _record_path(selection_id, runtime_root)
    with _proposal_lock("devc_" + selection_id.split("_", 1)[1], _runtime_root(runtime_root)):
        existing = _read_json(record_path)
        if existing:
            if not validate_test_selection(existing).get("ok"):
                raise ValueError("stored_test_selection_invalid")
            return {**existing, "operation_status": "restored"}
        surfaces = _classify_surfaces(changed_paths)
        selected, inventory, _depth = _select_tests(workspace, changed_paths, surfaces, trusted_test_root=Path(source_root).expanduser().resolve(strict=True))
        focused = sum(1 for row in selected if row["tier"] == "focused")
        regression = len(selected) - focused
        risk = "high" if any(s in surfaces for s in ("release_control", "privacy_security", "conversation", "coding_pipeline", "self_modification")) or len(changed_paths) >= 4 else "medium" if len(changed_paths) >= 2 or "python_runtime" in surfaces else "low"
        record: dict[str, Any] = {
            "ok": True, "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
            "status": "intelligent_test_selection_ready", "phase": "selected", "selection_id": selection_id,
            "source_operation_id": source_operation_id, "source_result_digest": source_result_digest,
            "candidate_manifest_digest": result.get("candidate_manifest_digest", ""),
            "candidate_source_manifest_digest": candidate_manifest["source_manifest_digest"],
            "changed_paths": changed_paths, "changed_path_count": len(changed_paths), "affected_surfaces": surfaces,
            "affected_surface_digest": _digest(surfaces), "risk_band": risk,
            "test_inventory_count": len(inventory), "test_inventory_digest": _digest(inventory),
            "selected_tests": selected, "selected_test_count": len(selected), "focused_test_count": focused, "regression_test_count": regression,
            "selection_policy_version": CONTRACT_VERSION, "selection_explanation_content_minimized": True,
            "test_ownership_integrity": "preserved", "supplemental_candidate_tests": supplemental_candidate_tests,
            "tests_executed": False, "provider_contacted": False, "commands_executed": False,
            "active_source_modified": False, "candidate_workspace_modified": False,
            "operator_review_required": True, "content_minimized": True,
            **TEST_SELECTION_DENIED_AUTHORITY,
        }
        record["selection_digest"] = _digest(_semantic_payload(record))
        record["record_digest"] = _record_digest(record)
        _write_json(record_path, record)
        return {**record, "operation_status": "created"}


def load_test_selection(selection_id: str, *, runtime_root: str | Path | None) -> dict[str, Any]:
    return _read_json(_record_path(selection_id, runtime_root))


def public_test_selection(record: Mapping[str, Any]) -> dict[str, Any]:
    hidden = {"record_digest"}
    return {k: v for k, v in record.items() if k not in hidden}


__all__ = [
    "CONTRACT_VERSION", "TEST_SELECTION_DENIED_AUTHORITY", "prepare_intelligent_test_selection",
    "load_test_selection", "validate_test_selection", "public_test_selection",
    "_digest", "_record_digest", "_write_json", "_record_path", "_runtime_root", "_classify_surfaces", "_select_tests", "_semantic_payload", "_is_test_path",
]
