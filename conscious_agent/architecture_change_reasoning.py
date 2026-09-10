from __future__ import annotations
"""Evidence-backed repository architecture and change-impact reasoning.

This layer composes the existing repository/project-understanding evidence rather
than creating a second source-of-truth. It is deliberately read-only: it can
inspect architecture, predict refactor hazards, and prepare a migration plan,
but cannot edit, execute, approve, install, or promote anything.
"""

import ast
import math
import re
from collections import Counter, defaultdict, deque
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from project_evidence_store import DENIED_AUTHORITY, atomic_json, digest, evidence_root, read_json, seal, valid
from repository_inventory import build_repository_inventory, load_repository_inventory
from symbol_graph import build_symbol_graph, load_symbol_graph

CONTRACT_VERSION = "v2503.7.2"
MAX_SCAN_BYTES = 8 * 1024 * 1024
MAX_TRANSITIVE_DEPTH = 12
MAX_PUBLIC_FINDINGS = 32

_RESPONSIBILITY_TERMS: dict[str, tuple[str, ...]] = {
    "conversation": ("conversation", "chat", "response", "utterance", "dialog", "message", "speech"),
    "memory": ("memory", "recall", "episod", "semantic", "entity", "relationship", "journal", "context"),
    "cognition": ("cognition", "belief", "reflect", "attention", "curiosity", "motivation", "goal", "deliber", "reason"),
    "planning": ("plan", "roadmap", "milestone", "schedule", "priority", "dependency"),
    "development": ("develop", "maintenance", "coding", "implementation", "patch", "repair", "diagnos", "project", "workspace"),
    "verification": ("verify", "verification", "test", "benchmark", "audit", "check", "quality"),
    "governance": ("govern", "authority", "approval", "authorization", "permission", "policy", "admission"),
    "release": ("release", "install", "rollback", "promotion", "checkpoint", "package", "backup"),
    "provider": ("provider", "model", "ollama", "inference", "embedding", "runtime_adapter"),
    "interface": ("dashboard", "desktop", "api", "http", "route", "cli", "ui", "surface"),
    "persistence": ("store", "storage", "ledger", "registry", "cache", "index", "database", "state"),
    "security_privacy": ("privacy", "secret", "security", "redact", "credential", "tamper", "sandbox", "isolation"),
}

_TEST_NAME_RE = re.compile(r"(^|/)(test[^/]*|tests|tools)(/|$)", re.I)
_SOURCE_FILENAME_RE = re.compile(r"(?P<name>[A-Za-z0-9_.-]+\.(?:py|js|ts|jsx|tsx|json|md|toml|yaml|yml))")


def _record_path(analysis_id: str, runtime_root=None) -> Path:
    return evidence_root("architecture_change_reasoning", runtime_root) / "records" / f"{analysis_id}.json"


def _plan_path(plan_id: str, runtime_root=None) -> Path:
    return evidence_root("architecture_change_reasoning", runtime_root) / "plans" / f"{plan_id}.json"


def _norm_rel(value: str) -> str:
    raw = str(value or "").replace("\\", "/").strip().lstrip("/")
    if not raw:
        return ""
    p = PurePosixPath(raw)
    if p.is_absolute() or ".." in p.parts:
        return ""
    return p.as_posix()


def _is_test_path(rel: str, row: dict[str, Any] | None = None) -> bool:
    return bool((row or {}).get("test")) or bool(_TEST_NAME_RE.search(rel)) or PurePosixPath(rel).name.startswith("test_")


def _module_parts(rel: str) -> list[str]:
    p = PurePosixPath(rel)
    parts = list(p.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return parts


def _resolve_python_import(source_rel: str, node: ast.AST, known_paths: set[str]) -> set[str]:
    src_parts = _module_parts(source_rel)
    package = src_parts[:-1]
    modules: list[str] = []
    if isinstance(node, ast.Import):
        modules.extend(alias.name for alias in node.names)
    elif isinstance(node, ast.ImportFrom):
        level = int(node.level or 0)
        base = list(package)
        if level:
            trim = max(0, level - 1)
            if trim:
                base = base[:-trim] if trim <= len(base) else []
        else:
            base = []
        mod_parts = str(node.module or "").split(".") if node.module else []
        base = base + [x for x in mod_parts if x]
        if base:
            modules.append(".".join(base))
        for alias in node.names:
            if alias.name != "*":
                modules.append(".".join(base + [alias.name]))
    out: set[str] = set()
    for module in modules:
        if not module:
            continue
        rel = module.replace(".", "/")
        for candidate in (f"{rel}.py", f"{rel}/__init__.py"):
            if candidate in known_paths:
                out.add(candidate)
        for prefix in ("conscious_agent", "src", "lib", "app"):
            for candidate in (f"{prefix}/{rel}.py", f"{prefix}/{rel}/__init__.py"):
                if candidate in known_paths:
                    out.add(candidate)
    return out


def _responsibilities(rel: str, symbols: Iterable[str]) -> list[dict[str, Any]]:
    rel_low = rel.lower()
    symbol_list = [str(x).lower() for x in symbols]
    rows = []
    for responsibility, terms in _RESPONSIBILITY_TERMS.items():
        filename_hits = sorted({term for term in terms if term in rel_low})
        supporting_symbols = 0
        evidence_terms: set[str] = set(filename_hits)
        for symbol in symbol_list:
            hits = [term for term in terms if term in symbol]
            if hits:
                supporting_symbols += 1
                evidence_terms.update(hits)
        if filename_hits or supporting_symbols:
            score = 0.52 if filename_hits else 0.20
            score += min(0.42, 0.09 * math.log2(1 + supporting_symbols))
            rows.append({
                "responsibility": responsibility,
                "score": round(min(1.0, score), 3),
                "filename_evidence": bool(filename_hits),
                "supporting_symbol_count": supporting_symbols,
                "evidence_terms": sorted(evidence_terms)[:8],
            })
    rows.sort(key=lambda x: (-bool(x.get("filename_evidence")), -float(x["score"]), -int(x.get("supporting_symbol_count") or 0), str(x["responsibility"])))
    return rows


def _suggested_owner(responsibilities: list[dict[str, Any]]) -> str:
    if not responsibilities:
        return "unclassified"
    primary = str(responsibilities[0]["responsibility"])
    return {
        "conversation": "conversation",
        "memory": "memory",
        "cognition": "cognition",
        "planning": "cognition/planning",
        "development": "development",
        "verification": "development/verification",
        "governance": "governance",
        "release": "governance/release",
        "provider": "runtime/providers",
        "interface": "interface",
        "persistence": "persistence",
        "security_privacy": "governance/security",
    }.get(primary, primary)


def _resolve_symbol_import(source_rel: str, target: str, known_paths: set[str]) -> str:
    raw = str(target or "").strip().lstrip(".")
    if not raw:
        return ""
    module_rel = raw.replace(".", "/")
    source_dir = PurePosixPath(source_rel).parent
    candidates: list[str] = []
    if str(source_dir) not in {"", "."}:
        candidates.extend([f"{source_dir.as_posix()}/{module_rel}.py", f"{source_dir.as_posix()}/{module_rel}/__init__.py"])
    candidates.extend([f"{module_rel}.py", f"{module_rel}/__init__.py"])
    if not raw.startswith("conscious_agent."):
        candidates.extend([f"conscious_agent/{module_rel}.py", f"conscious_agent/{module_rel}/__init__.py"])
    for candidate in candidates:
        if candidate in known_paths and candidate != source_rel:
            return candidate
    return ""




def _structural_filename_use(text: str, filename: str) -> bool:
    name = re.escape(str(filename))
    ops = r"(?:read_text|read_bytes|write_text|write_bytes|stat|exists|is_file|unlink|replace|rename)"
    patterns = (
        rf"\bopen\s*\([\s\S]{{0,240}}?[\"'][^\"']*{name}[^\"']*[\"']",
        rf"\bPath\s*\([\s\S]{{0,240}}?[\"'][^\"']*{name}[^\"']*[\"'][\s\S]{{0,120}}?\)\s*\.\s*{ops}\s*\(",
        rf"[\"'][^\"']*{name}[^\"']*[\"'][^\n]{{0,180}}?\.\s*{ops}\s*\(",
    )
    return any(re.search(pattern, text) for pattern in patterns)

def _scan_source(root: Path, rows: list[dict[str, Any]], target_paths: Iterable[str] = (), *, import_edges: Iterable[dict[str, Any]] = ()) -> dict[str, Any]:
    known_paths = {str(x.get("relative_path")) for x in rows}
    path_by_digest = {str(x.get("relative_path_digest") or ""): str(x.get("relative_path") or "") for x in rows}
    requested_targets = {str(x) for x in target_paths}
    basename_to_paths: defaultdict[str, set[str]] = defaultdict(set)
    for rel in requested_targets:
        if rel in known_paths:
            basename_to_paths[PurePosixPath(rel).name].add(rel)
    target_basenames = tuple(sorted(basename_to_paths))

    forward: defaultdict[str, set[str]] = defaultdict(set)
    reverse: defaultdict[str, set[str]] = defaultdict(set)
    source_filename_references: defaultdict[str, set[str]] = defaultdict(set)
    source_filename_consumers: defaultdict[str, set[str]] = defaultdict(set)
    symbol_names: defaultdict[str, list[str]] = defaultdict(list)
    metrics: dict[str, dict[str, Any]] = {}
    degraded: list[str] = []

    retained_graph = False
    for edge in import_edges or ():
        if str(edge.get("edge_kind") or "") != "import":
            continue
        source_rel = path_by_digest.get(str(edge.get("source_path_digest") or ""), "")
        target_rel = _resolve_symbol_import(source_rel, str(edge.get("target") or ""), known_paths) if source_rel else ""
        if source_rel and target_rel:
            forward[source_rel].add(target_rel); reverse[target_rel].add(source_rel); retained_graph = True

    target_import_terms = tuple(sorted({PurePosixPath(rel).stem for rel in requested_targets if rel in known_paths and PurePosixPath(rel).stem}))
    target_import_re = None
    if target_import_terms:
        alternation = "|".join(re.escape(term) for term in sorted(target_import_terms, key=len, reverse=True))
        target_import_re = re.compile(rf"(?m)^\s*(?:from|import)\s+[^\n]*(?<![A-Za-z0-9_])(?:{alternation})(?![A-Za-z0-9_])")

    for row in rows:
        rel = str(row.get("relative_path") or "")
        suffix = str(row.get("suffix") or PurePosixPath(rel).suffix).lower()
        if suffix != ".py" or int(row.get("size_bytes") or 0) > MAX_SCAN_BYTES:
            continue
        p = root / rel
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            degraded.append(rel); continue
        needs_target_metrics = rel in requested_targets
        mentions_filename = bool(target_basenames and any(name in text for name in target_basenames))
        mentions_import_target = bool(target_import_re and target_import_re.search(text))
        if mentions_filename:
            for name in target_basenames:
                if name not in text:
                    continue
                for target in basename_to_paths.get(name, ()):
                    if target == rel:
                        continue
                    source_filename_references[target].add(rel)
                    if _structural_filename_use(text, name):
                        source_filename_consumers[target].add(rel)

        needs_parse = needs_target_metrics or mentions_import_target or not retained_graph
        if not needs_parse:
            continue
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError, RecursionError):
            degraded.append(rel); continue

        top_symbols: list[str] = []
        classes = functions = 0
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes += 1; top_symbols.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions += 1; top_symbols.append(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)) and (not retained_graph or mentions_import_target):
                for target in _resolve_python_import(rel, node, known_paths):
                    if target != rel:
                        forward[rel].add(target); reverse[target].add(rel)
        if needs_target_metrics:
            symbol_names[rel] = top_symbols
            metrics[rel] = {
                "line_count": text.count("\n") + (0 if not text else 1),
                "top_level_symbol_count": len(top_symbols),
                "class_count": classes,
                "function_count": functions,
            }

    return {"forward": forward, "reverse": reverse, "filename_references": source_filename_references,
            "filename_consumers": source_filename_consumers, "symbols": symbol_names, "metrics": metrics, "degraded": degraded}


def _dependency_cycles(forward: dict[str, set[str]]) -> list[list[str]]:
    index = 0; stack: list[str] = []; on_stack: set[str] = set(); indices: dict[str, int] = {}; low: dict[str, int] = {}; components: list[list[str]] = []
    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index; low[node] = index; index += 1; stack.append(node); on_stack.add(node)
        for nxt in sorted(forward.get(node, ())):
            if nxt not in indices:
                visit(nxt); low[node] = min(low[node], low[nxt])
            elif nxt in on_stack:
                low[node] = min(low[node], indices[nxt])
        if low[node] == indices[node]:
            comp = []
            while stack:
                item = stack.pop(); on_stack.discard(item); comp.append(item)
                if item == node: break
            if len(comp) > 1 or (len(comp) == 1 and comp[0] in forward.get(comp[0], set())):
                components.append(sorted(comp))
    nodes = set(forward) | {x for values in forward.values() for x in values}
    for node in sorted(nodes):
        if node not in indices: visit(node)
    components.sort(key=lambda c: (len(c), c))
    return components


def build_architecture_change_assessment(source_root: str | Path, target_paths: Iterable[str], *, runtime_root=None, now_unix: int | None = None, evidence_workspace_digest: str = "") -> dict[str, Any]:
    root = Path(source_root).resolve()
    if evidence_workspace_digest:
        wid = str(evidence_workspace_digest)
        sg = load_symbol_graph(wid, runtime_root=runtime_root, include_private=True)
        if not sg:
            return {"ok": False, "status": "architecture_evidence_not_found", "action_executed": False, **DENIED_AUTHORITY}
        model_pub = {"workspace_digest": wid, "source_manifest_digest": sg.get("source_manifest_digest")}
    else:
        sg_pub = build_symbol_graph(root, runtime_root=runtime_root, now_unix=now_unix)["symbol_graph"]
        wid = str(sg_pub["workspace_digest"])
        model_pub = {"workspace_digest": wid, "source_manifest_digest": sg_pub.get("source_manifest_digest")}
        sg = load_symbol_graph(wid, runtime_root=runtime_root, include_private=True)
    inv = load_repository_inventory(wid, runtime_root=runtime_root, include_private=True)
    rows = list(inv.get("files") or []); by_path = {str(x.get("relative_path")): x for x in rows}
    requested: list[str] = []; invalid: list[str] = []
    for raw in target_paths or []:
        rel = _norm_rel(str(raw))
        if not rel: invalid.append(digest(str(raw)))
        elif rel not in requested: requested.append(rel)
    known = [x for x in requested if x in by_path]; unknown = [x for x in requested if x not in by_path]
    scan = _scan_source(root, rows, known, import_edges=sg.get("edges") or ()); dependency_cycles = _dependency_cycles(scan["forward"]); cycle_members = {p for component in dependency_cycles for p in component}

    findings: list[dict[str, Any]] = []; all_affected: set[str] = set(known); all_tests: set[str] = set(); all_filename_consumers: set[str] = set(); max_risk = 0
    risk_names = {0: "low", 1: "moderate", 2: "high", 3: "very_high"}
    for target in known:
        direct = set(scan["reverse"].get(target, ())); transitive = set(direct); depth = {x: 1 for x in direct}; q = deque(sorted(direct))
        while q:
            cur = q.popleft()
            if depth[cur] >= MAX_TRANSITIVE_DEPTH: continue
            for caller in scan["reverse"].get(cur, ()):
                if caller not in transitive and caller != target:
                    transitive.add(caller); depth[caller] = depth[cur] + 1; q.append(caller)
        filename_references = set(scan["filename_references"].get(target, ())); filename_consumers = set(scan["filename_consumers"].get(target, ()))
        verification_reach = set(transitive) | set(direct) | set(filename_consumers); verification_depth = {x: 1 for x in verification_reach}; vq = deque(sorted(verification_reach))
        while vq:
            cur = vq.popleft()
            if verification_depth.get(cur, 1) >= MAX_TRANSITIVE_DEPTH: continue
            for caller in scan["reverse"].get(cur, ()):
                if caller != target and caller not in verification_reach:
                    verification_reach.add(caller); verification_depth[caller] = verification_depth.get(cur, 1) + 1; vq.append(caller)
        candidate_tests = {x for x in verification_reach if _is_test_path(x, by_path.get(x))}
        test_candidate_rows = []
        for test_path in sorted(candidate_tests):
            reasons = []
            if test_path in direct: reasons.append("direct_importer")
            if test_path in filename_consumers: reasons.append("structural_source_consumer")
            if test_path in transitive and test_path not in direct: reasons.append("transitive_importer")
            if test_path not in transitive and test_path not in filename_consumers: reasons.append("consumer_dependency")
            priority = 0 if "structural_source_consumer" in reasons else 1 if "direct_importer" in reasons else 2 if "consumer_dependency" in reasons else 3
            test_candidate_rows.append({"path": test_path, "path_digest": digest(test_path), "priority": priority, "reasons": reasons})
        test_candidate_rows.sort(key=lambda x: (int(x["priority"]), str(x["path"])))
        symbols = list(scan["symbols"].get(target, ())); responsibilities = _responsibilities(target, symbols); metric = dict(scan["metrics"].get(target) or {})
        responsibility_count = len([x for x in responsibilities if float(x["score"]) >= 0.42])
        risk = 0; reasons: list[str] = []
        if len(direct) >= 8: risk += 1; reasons.append("many_direct_importers")
        if len(transitive) >= 20: risk += 1; reasons.append("broad_transitive_blast_radius")
        if filename_consumers: risk += 2; reasons.append("source_filename_contracts")
        if int(metric.get("line_count") or 0) >= 1500: risk += 1; reasons.append("large_module")
        if int(metric.get("line_count") or 0) >= 5000: risk += 1; reasons.append("very_large_module")
        if responsibility_count >= 4: risk += 1; reasons.append("mixed_responsibilities")
        if any(tok in target.lower() for tok in ("authority", "approval", "rollback", "release", "install", "secret", "privacy")):
            risk += 1; reasons.append("governance_or_trust_surface")
        risk = min(3, risk); max_risk = max(max_risk, risk); compatibility_facade = bool(filename_consumers) or len(direct) >= 8
        strategy = "extract_behind_compatibility_facade" if compatibility_facade else ("bounded_extract_then_migrate_callers" if int(metric.get("line_count") or 0) >= 800 else "direct_bounded_relocation")
        finding = {"target_path": target, "target_path_digest": digest(target), "metrics": metric, "top_level_symbols": symbols[:256], "responsibilities": responsibilities,
                   "suggested_owner": _suggested_owner(responsibilities), "direct_importers": sorted(direct), "transitive_importers": sorted(transitive),
                   "filename_references": sorted(filename_references), "filename_bound_consumers": sorted(filename_consumers), "candidate_tests": sorted(candidate_tests), "test_candidates": test_candidate_rows,
                   "direct_importer_count": len(direct), "transitive_importer_count": len(transitive), "filename_reference_count": len(filename_references), "filename_bound_consumer_count": len(filename_consumers),
                   "candidate_test_count": len(candidate_tests), "test_candidate_reason_counts": dict(Counter(reason for row in test_candidate_rows for reason in row.get("reasons") or [])),
                   "risk": risk_names[risk], "risk_reasons": reasons, "compatibility_facade_recommended": compatibility_facade, "recommended_strategy": strategy,
                   "in_dependency_cycle": target in cycle_members, "predictions_not_proof": True}
        findings.append(finding); all_affected |= transitive | filename_consumers; all_tests |= candidate_tests; all_filename_consumers |= filename_consumers

    uncertainty: list[dict[str, Any]] = []
    if unknown: uncertainty.append({"kind": "unknown_target_paths", "severity": "high", "count": len(unknown), "evidence_digest": digest(unknown)})
    if invalid: uncertainty.append({"kind": "invalid_target_paths", "severity": "high", "count": len(invalid), "evidence_digest": digest(invalid)})
    if scan["degraded"]: uncertainty.append({"kind": "degraded_python_parse", "severity": "medium", "count": len(scan["degraded"]), "evidence_digest": digest(sorted(scan["degraded"]))})
    if int(sg.get("degraded_parser_count") or 0): uncertainty.append({"kind": "existing_degraded_symbol_evidence", "severity": "medium", "count": int(sg.get("degraded_parser_count") or 0), "evidence_digest": digest(sg.get("degraded_parser_count"))})

    analysis_id = "architecture-impact-" + digest({"workspace": wid, "manifest": model_pub.get("source_manifest_digest"), "targets": requested})[:24]
    row = seal({"contract_version": CONTRACT_VERSION, "analysis_id": analysis_id, "workspace_digest": wid, "source_manifest_digest": model_pub.get("source_manifest_digest"),
                "requested_paths": requested, "known_paths": known, "unknown_path_digests": [digest(x) for x in unknown], "invalid_path_digests": invalid, "findings": findings,
                "affected_paths": sorted(all_affected), "candidate_tests": sorted(all_tests), "filename_bound_consumers": sorted(all_filename_consumers),
                "dependency_cycles": dependency_cycles, "dependency_cycle_count": len(dependency_cycles), "max_risk": risk_names[max_risk], "uncertainty": uncertainty,
                "complete": not any(x.get("severity") == "high" for x in uncertainty), "tests_executed": False, "source_modified": False, "provider_contacted": False, "action_executed": False, **DENIED_AUTHORITY})
    atomic_json(_record_path(analysis_id, runtime_root), row)
    return {"ok": bool(known) and not any(x.get("severity") == "high" for x in uncertainty), "status": "architecture_change_assessment_ready" if known and not uncertainty else "architecture_change_assessment_uncertain",
            "assessment": public_architecture_change_assessment(row), "action_executed": False, **DENIED_AUTHORITY}


def public_architecture_change_assessment(row: dict[str, Any]) -> dict[str, Any]:
    return {"contract_version": CONTRACT_VERSION, "analysis_id": row.get("analysis_id"), "workspace_digest": row.get("workspace_digest"), "source_manifest_digest": row.get("source_manifest_digest"),
            "requested_path_count": len(row.get("requested_paths") or []), "known_path_count": len(row.get("known_paths") or []), "unknown_path_count": len(row.get("unknown_path_digests") or []),
            "invalid_path_count": len(row.get("invalid_path_digests") or []), "affected_path_count": len(row.get("affected_paths") or []), "candidate_test_count": len(row.get("candidate_tests") or []),
            "filename_bound_consumer_count": len(row.get("filename_bound_consumers") or []), "dependency_cycle_count": int(row.get("dependency_cycle_count") or 0), "max_risk": row.get("max_risk"),
            "target_summaries": [{"target_path_digest": x.get("target_path_digest"), "line_count": int((x.get("metrics") or {}).get("line_count") or 0),
                                  "top_level_symbol_count": int((x.get("metrics") or {}).get("top_level_symbol_count") or 0), "responsibilities": [r.get("responsibility") for r in (x.get("responsibilities") or [])[:8]],
                                  "suggested_owner": x.get("suggested_owner"), "direct_importer_count": int(x.get("direct_importer_count") or 0), "transitive_importer_count": int(x.get("transitive_importer_count") or 0),
                                  "filename_reference_count": int(x.get("filename_reference_count") or 0), "filename_bound_consumer_count": int(x.get("filename_bound_consumer_count") or 0),
                                  "candidate_test_count": int(x.get("candidate_test_count") or 0), "test_candidate_reason_counts": dict(x.get("test_candidate_reason_counts") or {}), "risk": x.get("risk"),
                                  "risk_reasons": list(x.get("risk_reasons") or []), "compatibility_facade_recommended": bool(x.get("compatibility_facade_recommended")),
                                  "recommended_strategy": x.get("recommended_strategy"), "in_dependency_cycle": bool(x.get("in_dependency_cycle"))} for x in row.get("findings") or []],
            "uncertainty_count": len(row.get("uncertainty") or []), "uncertainty": list(row.get("uncertainty") or [])[:MAX_PUBLIC_FINDINGS], "complete": bool(row.get("complete")),
            "predictions_not_proof": True, "tests_executed": False, "raw_source_content_exposed": False, "source_paths_exposed": False, "read_only": True, "action_executed": False, **DENIED_AUTHORITY}


def load_architecture_change_assessment(analysis_id: str, *, runtime_root=None, include_private: bool = False) -> dict[str, Any]:
    row = read_json(_record_path(str(analysis_id), runtime_root)); return (row if include_private else public_architecture_change_assessment(row)) if row and valid(row) else {}


def build_refactor_migration_plan(source_root: str | Path, target_paths: Iterable[str], *, objective: str = "improve architectural ownership while preserving behavior", runtime_root=None, analysis_id: str = "") -> dict[str, Any]:
    raw_targets = [str(x) for x in (target_paths or [])]
    requested = [_norm_rel(x) for x in raw_targets if _norm_rel(x)]
    if len(requested) != len(raw_targets):
        return {"ok": False, "status": "invalid_target_paths", "action_executed": False, **DENIED_AUTHORITY}
    if analysis_id:
        assessment = load_architecture_change_assessment(analysis_id, runtime_root=runtime_root, include_private=True); assessment_result = {"ok": bool(assessment), "assessment": {"analysis_id": analysis_id}}
    else:
        assessment_result = build_architecture_change_assessment(source_root, requested, runtime_root=runtime_root)
        assessment = load_architecture_change_assessment(assessment_result.get("assessment", {}).get("analysis_id", ""), runtime_root=runtime_root, include_private=True)
    if not assessment: return {"ok": False, "status": "assessment_required", "action_executed": False, **DENIED_AUTHORITY}
    finding_rows = [x for x in assessment.get("findings") or [] if not requested or str(x.get("target_path")) in requested]
    if requested and len(finding_rows) != len(set(requested)): return {"ok": False, "status": "assessment_target_mismatch", "action_executed": False, **DENIED_AUTHORITY}
    steps: list[dict[str, Any]] = []; sequence = 0
    for finding in finding_rows:
        target = str(finding.get("target_path") or ""); owner = str(finding.get("suggested_owner") or "unclassified")
        sequence += 1; steps.append({"sequence": sequence, "kind": "capture_baseline", "target_path": target, "acceptance": ["source digest recorded", "focused tests identified", "authority unchanged"]})
        if finding.get("compatibility_facade_recommended"):
            sequence += 1; steps.append({"sequence": sequence, "kind": "establish_compatibility_facade", "target_path": target, "destination_owner": owner, "acceptance": ["legacy import identity retained where required", "source-filename consumers remain valid"]})
        if len(finding.get("responsibilities") or []) >= 2 or int((finding.get("metrics") or {}).get("line_count") or 0) >= 800:
            sequence += 1; steps.append({"sequence": sequence, "kind": "extract_one_responsibility", "target_path": target, "destination_owner": owner, "acceptance": ["one bounded responsibility moved", "public behavior preserved", "focused tests pass"]})
        else:
            sequence += 1; steps.append({"sequence": sequence, "kind": "relocate_stable_owner", "target_path": target, "destination_owner": owner, "acceptance": ["canonical ownership established", "legacy callers preserved or migrated"]})
        sequence += 1; steps.append({"sequence": sequence, "kind": "migrate_active_callers", "target_path": target, "destination_owner": owner, "acceptance": ["active callers use canonical owner", "historical compatibility remains explicit"]})
        sequence += 1; steps.append({"sequence": sequence, "kind": "verify_slice", "target_path": target, "acceptance": ["candidate tests pass", "source parse/import gates pass", "no unrelated changes"]})
    sequence += 1; steps.append({"sequence": sequence, "kind": "campaign_checkpoint", "acceptance": ["combined regression passes", "source-only package clean", "remaining hazards recorded", "next bounded unit explicit"]})
    plan_id = "architecture-plan-" + digest({"analysis": assessment.get("analysis_id"), "objective": objective, "steps": [(x["kind"], x.get("target_path"), x.get("destination_owner")) for x in steps]})[:24]
    row = seal({"contract_version": CONTRACT_VERSION, "plan_id": plan_id, "analysis_id": assessment.get("analysis_id"), "workspace_digest": assessment.get("workspace_digest"),
                "source_manifest_digest": assessment.get("source_manifest_digest"), "objective": str(objective), "steps": steps, "step_count": len(steps),
                "requires_operator_authorization_before_mutation": True, "review_only": True, "source_modified": False, "tests_executed": False, "provider_contacted": False, "action_executed": False, **DENIED_AUTHORITY})
    atomic_json(_plan_path(plan_id, runtime_root), row)
    return {"ok": bool(assessment_result.get("ok")), "status": "refactor_migration_plan_ready", "plan": public_refactor_migration_plan(row), "action_executed": False, **DENIED_AUTHORITY}


def public_refactor_migration_plan(row: dict[str, Any]) -> dict[str, Any]:
    kinds = Counter(str(x.get("kind")) for x in row.get("steps") or [])
    return {"contract_version": CONTRACT_VERSION, "plan_id": row.get("plan_id"), "analysis_id": row.get("analysis_id"), "workspace_digest": row.get("workspace_digest"),
            "source_manifest_digest": row.get("source_manifest_digest"), "step_count": int(row.get("step_count") or 0), "step_kind_counts": dict(sorted(kinds.items())),
            "requires_operator_authorization_before_mutation": True, "review_only": True, "source_modified": False, "tests_executed": False, "source_paths_exposed": False, "action_executed": False, **DENIED_AUTHORITY}


def load_refactor_migration_plan(plan_id: str, *, runtime_root=None, include_private: bool = False) -> dict[str, Any]:
    row = read_json(_plan_path(str(plan_id), runtime_root)); return (row if include_private else public_refactor_migration_plan(row)) if row and valid(row) else {}


def process_architecture_change_reasoning_control(text: str, *, project_root=None, runtime_root=None) -> dict[str, Any]:
    raw = str(text or "").strip(); low = raw.lower()
    for prefix, mode in (("assess architecture impact:", "assess"), ("plan architecture refactor:", "plan")):
        if low.startswith(prefix):
            if not project_root: return {"active": True, "ok": False, "status": "project_root_required", "action_executed": False, **DENIED_AUTHORITY}
            paths = [x.strip() for x in raw[len(prefix):].split(",") if x.strip()]
            if not paths: return {"active": True, "ok": False, "status": "target_paths_required", "action_executed": False, **DENIED_AUTHORITY}
            result = build_architecture_change_assessment(project_root, paths, runtime_root=runtime_root) if mode == "assess" else build_refactor_migration_plan(project_root, paths, runtime_root=runtime_root)
            return {"active": True, **result}
    if ("architecture impact" in low or "architecture refactor" in low) and any(x in low for x in (" and apply", " and install", " and modify", " and execute", " and delete")):
        return {"active": True, "ok": False, "status": "read_only_scope_expansion_rejected", "action_executed": False, **DENIED_AUTHORITY}
    return {"active": False}


__all__ = ["CONTRACT_VERSION", "build_architecture_change_assessment", "public_architecture_change_assessment", "load_architecture_change_assessment", "build_refactor_migration_plan", "public_refactor_migration_plan", "load_refactor_migration_plan", "process_architecture_change_reasoning_control"]
