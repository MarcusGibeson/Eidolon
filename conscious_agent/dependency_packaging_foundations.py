from __future__ import annotations

"""v1275.0-v1275.2 dependency and packaging management foundations.

This layer inventories dependency intent and reproducible source-package intent.
It does not install packages, contact registries, mutate the active source tree,
or publish a release. Dependency declarations are evidence and plans until a
separate bounded execution authorization is supplied to the integration layer.
"""

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from isolated_self_modification_foundations import source_only_manifest, _is_link_like
from package_integrity import forbidden_runtime_path_matches, source_package_bytes
from environment_awareness_foundations import AUTHORITY_FLAGS as ENVIRONMENT_AUTHORITY_FLAGS

CONTRACT_VERSION = "v1275.2"
SCHEMA_VERSION = "1"
MAX_DEPENDENCY_FILES = 64
MAX_DECLARATIONS = 512
MAX_PACKAGE_FILES = 10000
MAX_FILE_BYTES = 8 * 1024 * 1024

DEPENDENCY_FILES = (
    "requirements.txt", "requirements-core.txt", "requirements-optional.txt", "requirements-test.txt",
    "pyproject.toml", "setup.cfg", "setup.py", "Pipfile", "Pipfile.lock", "poetry.lock", "uv.lock",
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
)
LOCK_FILES = frozenset({"Pipfile.lock", "poetry.lock", "uv.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"})
CONFIG_FILES = frozenset({"pyproject.toml", "setup.cfg", "setup.py", "Pipfile", "package.json"})
REQUIREMENT_FILE_RE = re.compile(r"^requirements(?:-[A-Za-z0-9_.-]+)?\.txt$")
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SPEC_RE = re.compile(r"^(~=|==|!=|<=|>=|<|>)([^,\s]+)$")

AUTHORITY_FLAGS = {
    **ENVIRONMENT_AUTHORITY_FLAGS,
    "dependency_inventory_is_install_authority": False,
    "dependency_plan_is_install_authority": False,
    "dependency_conflict_resolution_is_install_authority": False,
    "clean_install_plan_is_execution_authority": False,
    "package_manifest_is_release_authority": False,
    "package_reproducibility_is_publish_authority": False,
    "active_source_dependency_mutation_authorized": False,
    "registry_contact_authorized": False,
    "network_install_authorized": False,
    "dependency_install_authorized": False,
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _bytes_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_dependency_name(name: str) -> str:
    text = re.sub(r"[-_.]+", "-", str(name or "").strip()).lower()
    if not text or not _NAME_RE.fullmatch(str(name or "").strip()):
        raise ValueError("invalid_dependency_name")
    return text


def _version_tuple(value: str) -> tuple[int, ...] | None:
    token = str(value or "").strip()
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", token):
        return None
    return tuple(int(x) for x in token.split("."))


def _cmp_version(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    n = max(len(a), len(b))
    aa = a + (0,) * (n - len(a)); bb = b + (0,) * (n - len(b))
    return (aa > bb) - (aa < bb)


def parse_requirement_line(line: str, *, source_file: str = "requirements.txt", line_number: int = 0) -> dict[str, Any] | None:
    raw = str(line).strip()
    if not raw or raw.startswith("#"):
        return None
    if raw.startswith(("-r ", "--requirement ", "-c ", "--constraint ")):
        parts = raw.split(None, 1)
        if len(parts) != 2:
            raise ValueError("dependency_include_missing_path")
        rel = PurePosixPath(parts[1].replace("\\", "/"))
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("dependency_include_path_escape")
        return {
            "kind": "include" if parts[0] in {"-r", "--requirement"} else "constraint_include",
            "relative_path": rel.as_posix(), "source_file": source_file, "line_number": int(line_number),
        }
    if raw.startswith("-"):
        return {"kind": "unsupported_option", "option_digest": _digest(raw), "source_file": source_file, "line_number": int(line_number)}

    body, marker = (raw.split(";", 1) + [""])[:2] if ";" in raw else (raw, "")
    body = body.strip(); marker = marker.strip()
    direct_reference = ""
    if " @ " in body:
        name_part, direct = body.split(" @ ", 1)
        name_part = name_part.strip(); direct_reference = direct.strip()
        spec_text = ""
    else:
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]+\])?\s*(.*)$", body)
        if not m:
            return {"kind": "unparsed", "line_digest": _digest(raw), "source_file": source_file, "line_number": int(line_number)}
        name_part, spec_text = m.group(1), m.group(2).strip()
    name = normalize_dependency_name(name_part)
    specifiers: list[dict[str, str]] = []
    if spec_text:
        for chunk in [x.strip() for x in spec_text.split(",") if x.strip()]:
            sm = _SPEC_RE.fullmatch(chunk)
            if not sm:
                return {"kind": "unparsed", "name": name, "line_digest": _digest(raw), "source_file": source_file, "line_number": int(line_number)}
            specifiers.append({"operator": sm.group(1), "version": sm.group(2)})
    return {
        "kind": "requirement", "name": name, "specifiers": specifiers,
        "marker_digest": _digest(marker) if marker else "", "has_marker": bool(marker),
        "direct_reference": bool(direct_reference), "direct_reference_digest": _digest(direct_reference) if direct_reference else "",
        "source_file": source_file, "line_number": int(line_number),
    }


def _resolve_requirement_file(root: Path, relative: str) -> Path:
    text = str(relative or "")
    if "\\" in text or re.match(r"^[A-Za-z]:", text) or ":" in text:
        raise ValueError("dependency_file_path_ambiguous")
    rel = PurePosixPath(text)
    if rel.is_absolute() or not rel.parts or any(part in {"", ".", ".."} for part in rel.parts):
        raise ValueError("dependency_file_path_escape")
    if _is_link_like(root):
        raise ValueError("dependency_source_root_link_or_reparse_rejected")
    current = root.resolve(strict=True)
    for part in rel.parts:
        current = current / part
        if current.exists() or current.is_symlink():
            if _is_link_like(current):
                raise ValueError("dependency_file_link_or_reparse_rejected")
    path = (root / rel.as_posix()).resolve()
    if root.resolve(strict=True) != path and root.resolve(strict=True) not in path.parents:
        raise ValueError("dependency_file_path_escape")
    return path


def inventory_requirement_files(source_root: str | Path) -> dict[str, Any]:
    root = Path(source_root).expanduser().resolve(strict=True)
    queue = sorted({p.name for p in root.iterdir() if p.is_file() and REQUIREMENT_FILE_RE.fullmatch(p.name)})
    declarations: list[dict[str, Any]] = []
    visited: list[str] = []
    file_rows: list[dict[str, Any]] = []
    while queue:
        relative = queue.pop(0)
        if relative in visited:
            continue
        if len(visited) >= MAX_DEPENDENCY_FILES:
            raise ValueError("dependency_file_inventory_bound_exceeded")
        path = _resolve_requirement_file(root, relative)
        if not path.is_file():
            declarations.append({"kind": "missing_include", "relative_path": relative})
            continue
        raw = path.read_bytes()
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError("dependency_file_too_large")
        visited.append(relative)
        file_rows.append({"relative_path": relative, "size_bytes": len(raw), "content_digest": _bytes_digest(raw), "role": "requirements"})
        text = raw.decode("utf-8-sig")
        for lineno, line in enumerate(text.splitlines(), 1):
            row = parse_requirement_line(line, source_file=relative, line_number=lineno)
            if row is None:
                continue
            declarations.append(row)
            if len(declarations) > MAX_DECLARATIONS:
                raise ValueError("dependency_declaration_bound_exceeded")
            if row.get("kind") in {"include", "constraint_include"}:
                include = str(row.get("relative_path") or "")
                if include and include not in visited and include not in queue:
                    queue.append(include)
                    queue.sort()
    return {"files": file_rows, "declarations": declarations, "file_count": len(file_rows), "declaration_count": len(declarations)}


def inventory_dependency_intent(source_root: str | Path) -> dict[str, Any]:
    root = Path(source_root).expanduser().resolve(strict=True)
    req = inventory_requirement_files(root)
    known_rows = list(req["files"])
    known_paths = {x["relative_path"] for x in known_rows}
    for name in DEPENDENCY_FILES:
        path = root / name
        if path.is_file() and name not in known_paths:
            raw = path.read_bytes()
            if len(raw) > MAX_FILE_BYTES:
                raise ValueError("dependency_file_too_large")
            role = "lock" if name in LOCK_FILES else "configuration" if name in CONFIG_FILES else "dependency"
            known_rows.append({"relative_path": name, "size_bytes": len(raw), "content_digest": _bytes_digest(raw), "role": role})
    known_rows.sort(key=lambda x: x["relative_path"].casefold())
    result = {
        "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
        "dependency_files": known_rows, "declarations": req["declarations"],
        "dependency_file_count": len(known_rows), "declaration_count": len(req["declarations"]),
        "lock_file_count": sum(1 for x in known_rows if x["role"] == "lock"),
        "configuration_file_count": sum(1 for x in known_rows if x["role"] == "configuration"),
        "raw_dependency_file_contents_persisted": False,
        **AUTHORITY_FLAGS,
    }
    result["dependency_intent_digest"] = _digest({"dependency_files": known_rows, "declarations": req["declarations"]})
    return result


def _satisfies_pin(pin: tuple[int, ...], specifiers: Iterable[Mapping[str, str]]) -> bool | None:
    for spec in specifiers:
        op = str(spec.get("operator") or ""); v = _version_tuple(str(spec.get("version") or ""))
        if v is None:
            return None
        c = _cmp_version(pin, v)
        if op == "==" and c != 0: return False
        if op == ">=" and c < 0: return False
        if op == ">" and c <= 0: return False
        if op == "<=" and c > 0: return False
        if op == "<" and c >= 0: return False
        if op == "!=" and c == 0: return False
        if op == "~=":
            if c < 0: return False
    return True


def detect_dependency_conflicts(declarations: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    unsupported = 0
    for row in declarations:
        if row.get("kind") != "requirement":
            unsupported += int(row.get("kind") in {"unparsed", "unsupported_option"})
            continue
        groups.setdefault((str(row.get("name") or ""), str(row.get("marker_digest") or "")), []).append(row)
    conflicts: list[dict[str, Any]] = []
    uncertain: list[dict[str, Any]] = []
    for (name, marker), rows in sorted(groups.items()):
        direct = [r for r in rows if r.get("direct_reference")]
        normal = [r for r in rows if not r.get("direct_reference")]
        if direct and normal:
            conflicts.append({"name": name, "reason": "direct_reference_and_version_specification_overlap", "marker_digest": marker})
            continue
        if len({str(r.get("direct_reference_digest") or "") for r in direct}) > 1:
            conflicts.append({"name": name, "reason": "multiple_direct_references", "marker_digest": marker}); continue
        specs = [s for r in normal for s in (r.get("specifiers") or [])]
        pins = {_version_tuple(str(s.get("version") or "")) for s in specs if s.get("operator") == "=="}
        if None in pins:
            uncertain.append({"name": name, "reason": "non_numeric_exact_pin_not_proven", "marker_digest": marker}); pins.discard(None)
        if len(pins) > 1:
            conflicts.append({"name": name, "reason": "incompatible_exact_pins", "marker_digest": marker}); continue
        if len(pins) == 1:
            pin = next(iter(pins)); sat = _satisfies_pin(pin, specs)
            if sat is False:
                conflicts.append({"name": name, "reason": "exact_pin_violates_other_constraint", "marker_digest": marker}); continue
            if sat is None:
                uncertain.append({"name": name, "reason": "specifier_relationship_not_proven", "marker_digest": marker})
        bounds = []
        for s in specs:
            if s.get("operator") in {">", ">=", "<", "<="}:
                vt = _version_tuple(str(s.get("version") or ""))
                if vt is None:
                    uncertain.append({"name": name, "reason": "non_numeric_bound_not_proven", "marker_digest": marker}); continue
                bounds.append((str(s.get("operator")), vt))
        lowers = [(op, v) for op, v in bounds if op in {">", ">="}]
        uppers = [(op, v) for op, v in bounds if op in {"<", "<="}]
        if lowers and uppers:
            lo = max(lowers, key=lambda x: x[1]); hi = min(uppers, key=lambda x: x[1]); c = _cmp_version(lo[1], hi[1])
            if c > 0 or (c == 0 and (lo[0] == ">" or hi[0] == "<")):
                conflicts.append({"name": name, "reason": "lower_bound_exceeds_upper_bound", "marker_digest": marker})
    return {
        "ok": not conflicts, "status": "dependency_constraints_coherent" if not conflicts else "dependency_conflicts_detected",
        "conflicts": conflicts, "conflict_count": len(conflicts), "uncertain_relationships": uncertain,
        "uncertain_relationship_count": len(uncertain), "unsupported_declaration_count": unsupported,
        "conflict_free_is_install_authority": False, **AUTHORITY_FLAGS,
    }


def build_dependency_change_plan(source_root: str | Path, *, additions: Iterable[str] = (), removals: Iterable[str] = (), target_file: str = "requirements-core.txt") -> dict[str, Any]:
    root = Path(source_root).expanduser().resolve(strict=True)
    intent = inventory_dependency_intent(root)
    target = PurePosixPath(str(target_file).replace("\\", "/"))
    if target.is_absolute() or ".." in target.parts or not REQUIREMENT_FILE_RE.fullmatch(target.name):
        raise ValueError("dependency_plan_target_invalid")
    parsed_additions = []
    for idx, line in enumerate(list(additions)[:64], 1):
        row = parse_requirement_line(str(line), source_file=target.as_posix(), line_number=idx)
        if not row or row.get("kind") != "requirement":
            raise ValueError("dependency_plan_addition_must_be_requirement")
        parsed_additions.append(row)
    removal_names = sorted({normalize_dependency_name(x) for x in list(removals)[:64]})
    proposed = [x for x in intent["declarations"] if x.get("kind") == "requirement" and x.get("name") not in removal_names] + parsed_additions
    conflicts = detect_dependency_conflicts(proposed)
    plan = {
        "ok": conflicts["conflict_count"] == 0, "status": "dependency_change_plan_ready" if conflicts["conflict_count"] == 0 else "dependency_change_plan_blocked",
        "contract_version": CONTRACT_VERSION, "baseline_dependency_intent_digest": intent["dependency_intent_digest"],
        "target_file": target.as_posix(), "addition_count": len(parsed_additions), "removal_count": len(removal_names),
        "addition_digests": [_digest(x) for x in parsed_additions], "removal_names": removal_names,
        "conflict_count": conflicts["conflict_count"], "uncertain_relationship_count": conflicts["uncertain_relationship_count"],
        "requires_operator_review": True, "requires_separate_install_authorization": True,
        "active_source_modified": False, **AUTHORITY_FLAGS,
    }
    plan["plan_digest"] = _digest(plan)
    return plan


def build_reproducible_source_package_manifest(source_root: str | Path) -> dict[str, Any]:
    root = Path(source_root).expanduser().resolve(strict=True)
    base = source_only_manifest(root)
    if int(base.get("file_count") or 0) > MAX_PACKAGE_FILES:
        raise ValueError("package_file_inventory_bound_exceeded")
    rows = []
    for row in base.get("files") or []:
        rel = str(row.get("relative_path") or "")
        if forbidden_runtime_path_matches([rel]):
            raise ValueError("package_manifest_forbidden_runtime_entry")
        data = source_package_bytes(root, rel)
        rows.append({"relative_path": rel, "package_size_bytes": len(data), "package_content_digest": _bytes_digest(data)})
    manifest = {
        "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
        "source_manifest_digest": base.get("source_manifest_digest"), "source_file_count": base.get("file_count"),
        "package_files": rows, "package_file_count": len(rows),
        "source_only": True, "runtime_data_included": False, "private_state_included": False,
        "package_root": "Eidolon", "deterministic_order": True, **AUTHORITY_FLAGS,
    }
    manifest["package_manifest_digest"] = _digest(rows)
    return manifest


__all__ = [
    "CONTRACT_VERSION", "AUTHORITY_FLAGS", "DEPENDENCY_FILES", "LOCK_FILES", "CONFIG_FILES",
    "normalize_dependency_name", "parse_requirement_line", "inventory_requirement_files", "inventory_dependency_intent",
    "detect_dependency_conflicts", "build_dependency_change_plan", "build_reproducible_source_package_manifest", "_digest",
]
