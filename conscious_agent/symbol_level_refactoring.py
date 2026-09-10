from __future__ import annotations

"""Deterministic extraction of selected top-level Python functions.

The model may select symbols from an exact inventory. This module owns all
source surgery, dependency analysis, wrapper retention, and syntax validation.
"""

import ast
import builtins
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping


MAX_CANDIDATE_SYMBOLS = 48
MAX_SELECTED_SYMBOLS = 8
MAX_REQUESTED_SYMBOLS = 12
MAX_EXTERNAL_DEPENDENCIES = 16
MAX_COHESIVE_LINE_GAP = 35


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _objective_tokens(proposal: Mapping[str, Any]) -> set[str]:
    text = " ".join(
        str(proposal.get(key) or "")
        for key in ("improvement_class", "proposed_change", "expected_benefit")
    ).casefold().replace("_", " ")
    ignored = {
        "behind", "bounded", "extract", "extraction", "helpers", "module",
        "preserve", "retained", "source",
    }
    return {token for token in re.findall(r"[a-z][a-z0-9_]{3,}", text) if token not in ignored}


def _top_level_functions(text: str) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(text)
    rows: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in rows:
                raise ValueError("symbol_refactoring_duplicate_top_level_symbol")
            rows[node.name] = node
    return rows


def build_symbol_inventory(source_text: str, proposal: Mapping[str, Any]) -> list[dict[str, Any]]:
    functions = _top_level_functions(source_text)
    tokens = _objective_tokens(proposal)
    proposed_change = str(proposal.get("proposed_change") or "").casefold()
    helper_extraction = "helper" in proposed_change
    scored: list[tuple[int, int, str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for name, node in functions.items():
        if name.startswith("_build_self_maintenance_") and name.endswith("_dependencies"):
            continue
        if (
            len(node.body) == 1
            and isinstance(node.body[0], ast.Return)
            and isinstance(node.body[0].value, ast.Call)
            and isinstance(node.body[0].value.func, ast.Name)
            and node.body[0].value.func.id.endswith("_implementation")
        ):
            continue
        folded = name.casefold()
        score = sum(5 for token in tokens if token in folded)
        if "approval" in folded and "approval" in proposed_change:
            score += 4
        if "record" in folded and "record" in proposed_change:
            score += 3
        if "revocation" in folded and "revocation" in proposed_change:
            score += 8
        if helper_extraction and name.startswith("_"):
            score += 2
        if score:
            scored.append((-score, node.lineno, name, node))
    scored.sort()
    rows = [
        {
            "name": name,
            "line": node.lineno,
            "end_line": int(node.end_lineno or node.lineno),
            "async": isinstance(node, ast.AsyncFunctionDef),
        }
        for _, _, name, node in scored[:MAX_CANDIDATE_SYMBOLS]
    ]
    if helper_extraction:
        private_rows = [row for row in rows if str(row["name"]).startswith("_")]
        if len(private_rows) >= 2:
            rows = private_rows
    if not rows:
        raise ValueError("symbol_refactoring_candidate_inventory_empty")
    return rows


def build_symbol_selection_prompt(
    source_text: str,
    proposal: Mapping[str, Any],
    *,
    source_path: str,
    destination_path: str,
) -> tuple[str, list[dict[str, Any]]]:
    inventory = build_symbol_inventory(source_text, proposal)
    request = {
        "task": "Select one cohesive top-level function family for deterministic extraction. Return one JSON object and no code.",
        "authority": {
            "proposal_id": proposal.get("proposal_id"),
            "proposal_digest": proposal.get("proposal_digest"),
            "active_source_mutation_authorized": False,
            "workspace_only": True,
        },
        "objective": proposal.get("proposed_change"),
        "source_path": source_path,
        "destination_path": destination_path,
        "candidates": inventory,
        "response_schema": {
            "authority": {"proposal_id": "exact", "proposal_digest": "exact"},
            "symbols": ["exact_candidate_name"],
            "reason_code": "short_machine_readable_reason",
        },
        "constraints": {
            "minimum_symbols": 2,
            "maximum_symbols": MAX_REQUESTED_SYMBOLS,
            "exact_candidate_names_only": True,
            "prefer_private_helpers": True,
            "one_cohesive_family": True,
            "no_code": True,
        },
    }
    return json.dumps(request, sort_keys=True, separators=(",", ":")), inventory


def _mapping_candidates(raw: str) -> list[Mapping[str, Any]]:
    text = str(raw or "").strip()
    values: list[Mapping[str, Any]] = []
    try:
        value = json.loads(text)
        if isinstance(value, Mapping):
            values.append(value)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for match in re.finditer(r"\{", text):
            try:
                value, _ = decoder.raw_decode(text[match.start() :])
            except json.JSONDecodeError:
                continue
            if isinstance(value, Mapping) and "symbols" in value:
                values.append(value)
        for block in re.findall(r"```(?:json|python)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL):
            try:
                value = ast.literal_eval(block.strip())
            except (MemoryError, RecursionError, SyntaxError, ValueError):
                continue
            if isinstance(value, Mapping) and "symbols" in value:
                values.append(value)
    return list({_digest(value): value for value in values}.values())


def parse_symbol_selection(
    raw: str,
    proposal: Mapping[str, Any],
    inventory: list[Mapping[str, Any]],
) -> dict[str, Any]:
    candidates = _mapping_candidates(raw)
    if len(candidates) != 1:
        raise ValueError("symbol_refactoring_selection_not_single_object")
    value = candidates[0]
    authority = value.get("authority") or {}
    if authority.get("proposal_id") != proposal.get("proposal_id") or authority.get("proposal_digest") != proposal.get("proposal_digest"):
        raise ValueError("symbol_refactoring_selection_authority_rejected")
    symbols = value.get("symbols")
    if not isinstance(symbols, list) or not 1 <= len(symbols) <= len(inventory):
        raise ValueError("symbol_refactoring_selection_count_invalid")
    allowed = {str(row.get("name") or "") for row in inventory}
    normalized = [str(name or "") for name in symbols]
    if len(set(normalized)) != len(normalized) or any(name not in allowed for name in normalized):
        raise ValueError("symbol_refactoring_selection_outside_inventory")
    line_by_name = {str(row.get("name") or ""): int(row.get("line") or 0) for row in inventory}
    if len(normalized) == 1:
        inventory_ordered = sorted(allowed, key=lambda name: (line_by_name[name], name))
        inventory_groups: list[list[str]] = []
        for name in inventory_ordered:
            if not inventory_groups or line_by_name[name] - line_by_name[inventory_groups[-1][-1]] > MAX_COHESIVE_LINE_GAP:
                inventory_groups.append([name])
            else:
                inventory_groups[-1].append(name)
        anchored = [group for group in inventory_groups if normalized[0] in group and len(group) >= 2]
        if len(anchored) != 1:
            raise ValueError("symbol_refactoring_single_selection_has_no_family")
        normalized = anchored[0][:MAX_SELECTED_SYMBOLS]
    ordered = sorted(normalized, key=lambda name: (line_by_name[name], name))
    groups: list[list[str]] = []
    for name in ordered:
        if not groups or line_by_name[name] - line_by_name[groups[-1][-1]] > MAX_COHESIVE_LINE_GAP:
            groups.append([name])
        else:
            groups[-1].append(name)
    largest_size = max(len(group) for group in groups)
    largest = [group for group in groups if len(group) == largest_size]
    if largest_size < 2:
        raise ValueError("symbol_refactoring_cohesive_family_ambiguous")
    selected_family = min(largest, key=lambda group: (line_by_name[group[0]], group[0]))
    selected = selected_family[:MAX_SELECTED_SYMBOLS]
    return {
        "symbols": selected,
        "requested_symbols": normalized,
        "selection_normalized": selected != normalized,
        "normalization_code": (
            "largest_adjacent_family_source_order_tiebreak"
            if selected != normalized and len(largest) > 1
            else "unique_largest_adjacent_family"
            if selected != normalized
            else "none"
        ),
        "reason_code": re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(value.get("reason_code") or "model_selected"))[:80],
        "selection_digest": _digest(selected),
    }


def _imported_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.update(alias.asname or alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(alias.asname or alias.name for alias in node.names if alias.name != "*")
    return names


def _local_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names = {arg.arg for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)}
    if node.args.vararg:
        names.add(node.args.vararg.arg)
    if node.args.kwarg:
        names.add(node.args.kwarg.arg)
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, (ast.Store, ast.Del)):
            names.add(child.id)
        elif isinstance(child, ast.ExceptHandler) and child.name:
            names.add(str(child.name))
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and child is not node:
            names.add(child.name)
    return names


def _external_dependencies(
    nodes: list[ast.FunctionDef | ast.AsyncFunctionDef],
    *,
    selected: set[str],
    imported: set[str],
) -> list[str]:
    builtin_names = set(dir(builtins)) | {"True", "False", "None"}
    dependencies: set[str] = set()
    for node in nodes:
        local = _local_names(node)
        for child in ast.walk(node):
            if not isinstance(child, ast.Name) or not isinstance(child.ctx, ast.Load):
                continue
            if child.id in local or child.id in selected or child.id in imported or child.id in builtin_names:
                continue
            dependencies.add(child.id)
    if not dependencies or len(dependencies) > MAX_EXTERNAL_DEPENDENCIES:
        raise ValueError("symbol_refactoring_dependency_closure_invalid")
    return sorted(dependencies)


class _ImplementationTransformer(ast.NodeTransformer):
    def __init__(self, external: set[str], selected: set[str]) -> None:
        self.external = external
        self.selected = selected

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if isinstance(node.ctx, ast.Load) and node.id in self.external:
            return ast.copy_location(
                ast.Attribute(value=ast.Name(id="_deps", ctx=ast.Load()), attr=node.id, ctx=node.ctx),
                node,
            )
        return node

    def visit_Call(self, node: ast.Call) -> ast.AST:
        original_name = node.func.id if isinstance(node.func, ast.Name) else ""
        revised = self.generic_visit(node)
        if original_name in self.selected and isinstance(revised, ast.Call):
            if any(keyword.arg == "_deps" for keyword in revised.keywords):
                raise ValueError("symbol_refactoring_dependency_argument_collision")
            revised.keywords.append(ast.keyword(arg="_deps", value=ast.Name(id="_deps", ctx=ast.Load())))
        return revised


def _implementation_node(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    external: set[str],
    selected: set[str],
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    revised = copy.deepcopy(node)
    if revised.decorator_list:
        raise ValueError("symbol_refactoring_decorated_function_rejected")
    if any(arg.arg == "_deps" for arg in (*revised.args.posonlyargs, *revised.args.args, *revised.args.kwonlyargs)):
        raise ValueError("symbol_refactoring_reserved_argument_collision")
    revised.args.kwonlyargs.append(ast.arg(arg="_deps", annotation=ast.Name(id="SymbolDependencies", ctx=ast.Load())))
    revised.args.kw_defaults.append(None)
    revised = _ImplementationTransformer(external, selected).visit(revised)
    return ast.fix_missing_locations(revised)


def _wrapper_node(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    implementation_alias: str,
    dependency_factory: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    wrapper = copy.deepcopy(node)
    wrapper.decorator_list = []
    positional = [ast.Name(id=arg.arg, ctx=ast.Load()) for arg in (*wrapper.args.posonlyargs, *wrapper.args.args)]
    if wrapper.args.vararg:
        positional.append(ast.Starred(value=ast.Name(id=wrapper.args.vararg.arg, ctx=ast.Load()), ctx=ast.Load()))
    keywords = [ast.keyword(arg=arg.arg, value=ast.Name(id=arg.arg, ctx=ast.Load())) for arg in wrapper.args.kwonlyargs]
    if wrapper.args.kwarg:
        keywords.append(ast.keyword(arg=None, value=ast.Name(id=wrapper.args.kwarg.arg, ctx=ast.Load())))
    keywords.append(ast.keyword(arg="_deps", value=ast.Call(func=ast.Name(id=dependency_factory, ctx=ast.Load()), args=[], keywords=[])))
    call = ast.Call(func=ast.Name(id=implementation_alias, ctx=ast.Load()), args=positional, keywords=keywords)
    wrapper.body = [ast.Return(value=ast.Await(value=call))] if isinstance(wrapper, ast.AsyncFunctionDef) else [ast.Return(value=call)]
    return ast.fix_missing_locations(wrapper)


def build_symbol_extraction_changes(
    source_text: str,
    *,
    source_path: str,
    destination_path: str,
    symbols: list[str],
) -> dict[str, Any]:
    tree = ast.parse(source_text)
    functions = _top_level_functions(source_text)
    if any(name not in functions for name in symbols):
        raise ValueError("symbol_refactoring_selected_symbol_missing")
    selected = set(symbols)
    nodes = sorted((functions[name] for name in symbols), key=lambda node: node.lineno)
    # These imports are reproduced in every generated helper. Project-local
    # imports remain explicit injected dependencies to avoid hidden coupling.
    portable_imports = {"json", "Path", "Any"}
    dependencies = _external_dependencies(nodes, selected=selected, imported=portable_imports)
    module_stem = PurePosixPath(destination_path).stem
    class_name = "SymbolDependencies"
    dependency_alias = "_" + "".join(part.capitalize() for part in module_stem.split("_")) + class_name
    aliases = {name: f"_{name.lstrip('_')}_implementation" for name in symbols}
    if len(set(aliases.values())) != len(aliases):
        raise ValueError("symbol_refactoring_alias_collision")
    implementation_nodes = [
        _implementation_node(node, external=set(dependencies), selected=selected) for node in nodes
    ]
    helper_header = [
        "from __future__ import annotations",
        "",
        '"""Deterministically extracted symbol family; active wrappers retain public behavior."""',
        "",
        "import json",
        "from dataclasses import dataclass",
        "from pathlib import Path",
        "from typing import Any",
        "",
        "@dataclass(frozen=True)",
        f"class {class_name}:",
        *[f"    {name}: Any" for name in dependencies],
        "",
    ]
    helper_parts = ["\n".join(helper_header)]
    for node in implementation_nodes:
        helper_parts.append(ast.unparse(node))
    helper_text = "\n\n\n".join(helper_parts).rstrip() + "\n"
    ast.parse(helper_text, filename=destination_path)

    import_lines = [f"from {module_stem} import (", f"    {class_name} as {dependency_alias},"]
    for name in symbols:
        import_lines.append(f"    {name} as {aliases[name]},")
    import_lines.extend([")", ""])
    import_text = "\n".join(import_lines)
    import_nodes = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    if not import_nodes:
        raise ValueError("symbol_refactoring_import_block_missing")
    import_insertion_line = max(int(node.end_lineno or node.lineno) for node in import_nodes)

    factory_name = f"_build_{module_stem}_dependencies"
    factory_lines = [f"def {factory_name}() -> {dependency_alias}:", f"    return {dependency_alias}("]
    factory_lines.extend(f"        {name}={name}," for name in dependencies)
    factory_lines.extend(["    )", "", ""])
    factory_text = "\n".join(factory_lines)

    # Source line positions still refer to the pre-import text. Apply body replacements first.
    lines = source_text.splitlines(keepends=True)
    replacements: list[tuple[int, int, str]] = []
    for index, node in enumerate(nodes):
        wrapper = _wrapper_node(node, implementation_alias=aliases[node.name], dependency_factory=factory_name)
        wrapper_text = ast.unparse(wrapper).rstrip() + "\n\n"
        if index == 0:
            wrapper_text = factory_text + wrapper_text
        replacements.append((node.lineno - 1, int(node.end_lineno or node.lineno), wrapper_text))
    for start, end, replacement in sorted(replacements, reverse=True):
        lines[start:end] = [replacement]
    lines[import_insertion_line:import_insertion_line] = [import_text + "\n"]
    revised = "".join(lines)
    ast.parse(revised, filename=source_path)
    return {
        "source_content": revised,
        "destination_content": helper_text,
        "symbols": [node.name for node in nodes],
        "dependencies": dependencies,
        "symbol_count": len(nodes),
        "dependency_count": len(dependencies),
        "dependency_alias": dependency_alias,
        "transformation_digest": _digest(
            {"source_path": source_path, "destination_path": destination_path, "symbols": symbols, "dependencies": dependencies}
        ),
    }


__all__ = [
    "build_symbol_inventory", "build_symbol_selection_prompt", "parse_symbol_selection",
    "build_symbol_extraction_changes",
]
