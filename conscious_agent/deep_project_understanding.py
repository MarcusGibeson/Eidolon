from __future__ import annotations
"""Era 2 / Arc 5 portable deep-project-understanding layer.

This module deliberately composes the established v1311-v1320 project evidence
owners.  It does not execute projects, contact providers, mutate repositories, or
create a second project-memory/authority path.
"""
from collections import Counter, defaultdict, deque
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
import hashlib
import json
import re

from project_evidence_store import (
    DENIED_AUTHORITY,
    atomic_json,
    digest,
    evidence_root,
    read_json,
    seal,
    valid,
)
from repository_inventory import build_repository_inventory, load_repository_inventory
from symbol_graph import build_symbol_graph, load_symbol_graph
from dependency_graph import build_dependency_graph, load_dependency_graph
from runtime_topology import build_runtime_topology, load_runtime_topology
from behavioral_map import build_behavioral_map
from architecture_summaries import build_architecture_summaries

CONTRACT_VERSION = "v1625.9"
MAX_PUBLIC_ISSUES = 24
MAX_DATAFLOW_DEPTH = 8
MAX_GRAPH_NODES = 8192

_CONFIG_NAMES = {
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "pipfile",
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "tsconfig.json", "vite.config.js", "vite.config.ts", "webpack.config.js",
    "pom.xml", "build.gradle", "build.gradle.kts", "gradle.properties",
    "dockerfile", "docker-compose.yml", "docker-compose.yaml", ".env.example",
    "ruff.toml", "pytest.ini", "tox.ini", "mypy.ini", ".editorconfig",
}
_GENERATED_PARTS = {
    "dist", "build", "target", "coverage", ".next", ".nuxt", "generated",
    "gen", "out", "site", "htmlcov",
}
_RUNTIME_PARTS = {
    "data", "runtime", "logs", "cache", "caches", "sessions", "state",
    "install_backups", "proposal_workspaces", "provider_payloads",
}
_TEST_PARTS = {"test", "tests", "spec", "specs", "__tests__"}
_ENTRY_NAMES = {
    "main.py", "app.py", "server.py", "cli.py", "manage.py", "wsgi.py", "asgi.py",
    "index.js", "index.ts", "main.js", "main.ts", "server.js", "server.ts",
    "app.js", "app.ts", "program.cs", "main.java",
}
_BOUNDARY_FILES = {
    "__init__.py", "package.json", "pyproject.toml", "pom.xml", "build.gradle",
    "build.gradle.kts", "settings.gradle", "settings.gradle.kts",
}
_SCHEMA_HINTS = ("schema", "migration", "model", "models", "database", "db", ".sql")
_UI_HINTS = ("dashboard", "frontend", "static", "templates", "ui", "web", "view", "component")
_SECRET_HINTS = (".env", "secret", "credential", "token", "private_key", "id_rsa")


def _record_path(workspace_digest: str, runtime_root=None) -> Path:
    return evidence_root("deep_project_understanding", runtime_root) / "records" / f"{workspace_digest}.json"


def _impact_path(analysis_id: str, runtime_root=None) -> Path:
    return evidence_root("deep_project_understanding", runtime_root) / "impact" / f"{analysis_id}.json"


def _benchmark_path(benchmark_id: str, runtime_root=None) -> Path:
    return evidence_root("deep_project_understanding", runtime_root) / "benchmarks" / f"{benchmark_id}.json"


def _norm_rel(value: str) -> str:
    raw = str(value or "").replace("\\", "/").strip().lstrip("/")
    if not raw:
        return ""
    pure = PurePosixPath(raw)
    if pure.is_absolute() or ".." in pure.parts:
        return ""
    return pure.as_posix()


def _is_privateish(rel: str) -> bool:
    low = rel.lower()
    name = PurePosixPath(low).name
    return any(h in low for h in _SECRET_HINTS) or name in {"projects.json", "settings.json"}


def _module_key(rel: str) -> str:
    parts = PurePosixPath(rel).parts
    if not parts:
        return "root"
    if parts[0] in {"src", "lib", "app", "packages", "conscious_agent"} and len(parts) > 1:
        return "/".join(parts[:2])
    return parts[0]


def _kind_for_file(rel: str, *, is_test: bool = False) -> str:
    p = PurePosixPath(rel)
    low = rel.lower()
    parts = {x.lower() for x in p.parts}
    name = p.name.lower()
    if is_test or parts & _TEST_PARTS or name.startswith("test_") or name.endswith((".test.js", ".test.ts", ".spec.js", ".spec.ts")):
        return "test"
    if name in _CONFIG_NAMES or name.startswith(("dockerfile", ".github")):
        return "configuration"
    if parts & _GENERATED_PARTS:
        return "generated"
    if parts & _RUNTIME_PARTS:
        return "runtime_state"
    if _is_privateish(rel):
        return "private_or_secret"
    if name in _ENTRY_NAMES or name.startswith("main."):
        return "entry_point_candidate"
    if any(h in low for h in _SCHEMA_HINTS):
        return "schema_or_storage"
    if any(part in {"docs", "doc"} for part in parts) or p.suffix.lower() in {".md", ".rst"}:
        return "documentation"
    if any(h in low for h in _UI_HINTS):
        return "user_surface"
    return "source"


def _ownership_boundary(rel: str) -> str:
    p = PurePosixPath(rel)
    parts = p.parts
    if not parts:
        return "root"
    if len(parts) == 1:
        return "root"
    if parts[0] in {"src", "lib", "app", "packages", "conscious_agent", "tools"}:
        return "/".join(parts[: min(2, len(parts) - (1 if p.suffix else 0))]) or parts[0]
    return parts[0]


def _confidence(*, parser_degraded: bool = False, unresolved: bool = False, heuristic: bool = False) -> str:
    if parser_degraded or unresolved:
        return "low"
    if heuristic:
        return "medium"
    return "high"


def _public_issue(kind: str, severity: str, evidence: Any, guidance: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "severity": severity,
        "evidence_digest": digest(evidence),
        "guidance": guidance,
        "content_exposed": False,
    }


def build_deep_repository_model(source_root: str | Path, *, runtime_root=None, now_unix: int | None = None) -> dict[str, Any]:
    """Build a content-minimized architectural model from established evidence layers."""
    root = Path(source_root).resolve()
    inv_pub = build_repository_inventory(root, runtime_root=runtime_root, now_unix=now_unix)["inventory"]
    wid = str(inv_pub["workspace_digest"])
    manifest = str(inv_pub["source_manifest_digest"])
    existing = load_deep_repository_model(wid, runtime_root=runtime_root, include_private=True)
    if existing and existing.get("source_manifest_digest") == manifest:
        return {"ok": True, "status": "deep_repository_model_current", "repository_model": public_repository_model(existing), "action_executed": False, **DENIED_AUTHORITY}

    # Reuse the established graph owners.  Their persisted records remain the authority.
    build_symbol_graph(root, runtime_root=runtime_root, now_unix=now_unix)
    build_dependency_graph(root, runtime_root=runtime_root, now_unix=now_unix)
    build_runtime_topology(root, runtime_root=runtime_root, now_unix=now_unix)
    behavioral = build_behavioral_map(root, runtime_root=runtime_root, now_unix=now_unix)["behavioral_map"]
    summaries = build_architecture_summaries(root, runtime_root=runtime_root, now_unix=now_unix)["architecture_summaries"]
    inv = load_repository_inventory(wid, runtime_root=runtime_root, include_private=True)
    sg = load_symbol_graph(wid, runtime_root=runtime_root, include_private=True)
    dep = load_dependency_graph(wid, runtime_root=runtime_root, include_private=True)
    top = load_runtime_topology(wid, runtime_root=runtime_root, include_private=True)

    files = list(inv.get("files") or [])
    path_by_digest = {str(x.get("relative_path_digest")): str(x.get("relative_path")) for x in files}
    rows: list[dict[str, Any]] = []
    kind_counts: Counter[str] = Counter()
    module_counts: Counter[str] = Counter()
    ownership_counts: Counter[str] = Counter()
    privacy_issues: list[dict[str, Any]] = []
    for f in files:
        rel = str(f.get("relative_path") or "")
        kind = _kind_for_file(rel, is_test=bool(f.get("test")))
        module = _module_key(rel)
        owner = _ownership_boundary(rel)
        kind_counts[kind] += 1
        module_counts[module] += 1
        ownership_counts[owner] += 1
        if kind in {"runtime_state", "private_or_secret"}:
            privacy_issues.append(_public_issue(
                "source_runtime_boundary_risk" if kind == "runtime_state" else "private_source_risk",
                "high",
                {"path_digest": f.get("relative_path_digest"), "kind": kind},
                "Keep runtime/private material outside the source tree and require explicit local review.",
            ))
        rows.append({
            "relative_path": rel,
            "relative_path_digest": f.get("relative_path_digest"),
            "content_digest": f.get("content_digest"),
            "language": f.get("language"),
            "kind": kind,
            "module": module,
            "ownership_boundary": owner,
            "test": bool(f.get("test")),
        })

    # Entry points are candidate declarations only.  We refuse to turn source shape into live-runtime proof.
    topology_by_path: defaultdict[str, set[str]] = defaultdict(set)
    for n in top.get("nodes") or []:
        topology_by_path[str(n.get("source_path_digest"))].add(str(n.get("kind")))
    entry_candidates: list[dict[str, Any]] = []
    for r in rows:
        kinds = topology_by_path.get(str(r.get("relative_path_digest")), set())
        if r["kind"] == "entry_point_candidate" or kinds & {"route", "cli", "user_surface"}:
            entry_candidates.append({
                "relative_path": r["relative_path"],
                "relative_path_digest": r["relative_path_digest"],
                "declared_kinds": sorted(kinds),
                "confidence": _confidence(heuristic=(r["kind"] == "entry_point_candidate" and not kinds)),
                "live_runtime_verified": False,
            })

    # Internal dependency flows: keep private paths private, publish only counts/digests.
    flow_edges: list[dict[str, Any]] = []
    unresolved_edges = 0
    for e in dep.get("edges") or []:
        src = path_by_digest.get(str(e.get("source_path_digest")))
        dst = path_by_digest.get(str(e.get("target_path_digest")))
        if not src or not dst:
            unresolved_edges += 1
            continue
        flow_edges.append({
            "source_path": src,
            "source_path_digest": e.get("source_path_digest"),
            "target_path": dst,
            "target_path_digest": e.get("target_path_digest"),
            "kind": e.get("kind", "internal_import"),
            "confidence": "high",
        })

    issues = list(privacy_issues)
    if int(sg.get("degraded_parser_count") or 0):
        issues.append(_public_issue(
            "parser_degradation",
            "medium",
            {"count": int(sg.get("degraded_parser_count") or 0), "manifest": manifest},
            "Treat affected symbol and dependency claims as uncertain until a supported parser succeeds.",
        ))
    if unresolved_edges:
        issues.append(_public_issue(
            "unresolved_dependency_edges",
            "low",
            {"count": unresolved_edges, "manifest": manifest},
            "Preserve unresolved dependencies as unknown rather than inventing a target.",
        ))

    model = seal({
        "contract_version": CONTRACT_VERSION,
        "workspace_digest": wid,
        "source_manifest_digest": manifest,
        "file_count": len(rows),
        "files": rows,
        "kind_counts": dict(sorted(kind_counts.items())),
        "module_counts": dict(sorted(module_counts.items())),
        "ownership_counts": dict(sorted(ownership_counts.items())),
        "entry_points": entry_candidates,
        "flow_edges": flow_edges[:MAX_GRAPH_NODES],
        "dependency_edge_count": len(flow_edges),
        "unresolved_dependency_edge_count": unresolved_edges,
        "behavioral_map_digest": digest(behavioral),
        "architecture_summaries_digest": digest(summaries),
        "issues": issues[:MAX_PUBLIC_ISSUES],
        "generated_files_excluded_from_runtime_claims": True,
        "runtime_state_excluded_from_authority": True,
        "raw_source_content_persisted": False,
        "live_runtime_verified": False,
        "native_windows_verified": False,
        "provider_contacted": False,
        "source_modified": False,
        "action_executed": False,
        **DENIED_AUTHORITY,
    })
    atomic_json(_record_path(wid, runtime_root), model)
    return {"ok": not bool(privacy_issues), "status": "deep_repository_model_ready" if not privacy_issues else "deep_repository_model_boundary_risk", "repository_model": public_repository_model(model), "action_executed": False, **DENIED_AUTHORITY}


def public_repository_model(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "workspace_digest": row.get("workspace_digest"),
        "source_manifest_digest": row.get("source_manifest_digest"),
        "file_count": int(row.get("file_count") or 0),
        "kind_counts": dict(row.get("kind_counts") or {}),
        "module_count": len(row.get("module_counts") or {}),
        "ownership_boundary_count": len(row.get("ownership_counts") or {}),
        "entry_point_candidate_count": len(row.get("entry_points") or []),
        "dependency_edge_count": int(row.get("dependency_edge_count") or 0),
        "unresolved_dependency_edge_count": int(row.get("unresolved_dependency_edge_count") or 0),
        "issue_count": len(row.get("issues") or []),
        "issues": list(row.get("issues") or [])[:MAX_PUBLIC_ISSUES],
        "raw_source_content_exposed": False,
        "source_paths_exposed": False,
        "live_runtime_verified": False,
        "native_windows_verified": False,
        "provider_contacted": False,
        "read_only": True,
        "action_executed": False,
        **DENIED_AUTHORITY,
    }


def load_deep_repository_model(workspace_digest_value: str, *, runtime_root=None, include_private: bool = False) -> dict[str, Any]:
    row = read_json(_record_path(str(workspace_digest_value), runtime_root))
    if not row or not valid(row):
        return {}
    return row if include_private else public_repository_model(row)


def assess_repository_model_freshness(source_root: str | Path, *, runtime_root=None) -> dict[str, Any]:
    root = Path(source_root).resolve()
    current = build_repository_inventory(root, runtime_root=runtime_root)["inventory"]
    old = load_deep_repository_model(str(current["workspace_digest"]), runtime_root=runtime_root, include_private=True)
    same = bool(old) and old.get("source_manifest_digest") == current.get("source_manifest_digest")
    return {"ok": bool(old), "status": "current" if same else ("stale" if old else "missing"), "current": same, "action_executed": False, **DENIED_AUTHORITY}


def build_change_impact_reasoning(source_root: str | Path, changed_paths: Iterable[str], *, runtime_root=None, now_unix: int | None = None) -> dict[str, Any]:
    """Trace likely blast radius while explicitly retaining unknowns and confidence."""
    root = Path(source_root).resolve()
    model_result = build_deep_repository_model(root, runtime_root=runtime_root, now_unix=now_unix)
    pub_model = model_result["repository_model"]
    wid = str(pub_model["workspace_digest"])
    model = load_deep_repository_model(wid, runtime_root=runtime_root, include_private=True)
    inv = load_repository_inventory(wid, runtime_root=runtime_root, include_private=True)
    sg = load_symbol_graph(wid, runtime_root=runtime_root, include_private=True)

    by_path = {str(x.get("relative_path")): x for x in inv.get("files") or []}
    path_by_digest = {str(x.get("relative_path_digest")): str(x.get("relative_path")) for x in inv.get("files") or []}
    digest_by_path = {p: str(v.get("relative_path_digest")) for p, v in by_path.items()}
    requested: list[str] = []
    invalid: list[str] = []
    for raw in changed_paths or []:
        rel = _norm_rel(str(raw))
        if not rel:
            invalid.append(digest(str(raw)))
        elif rel not in requested:
            requested.append(rel)
    known = [p for p in requested if p in by_path]
    unknown = [p for p in requested if p not in by_path]

    reverse: defaultdict[str, set[str]] = defaultdict(set)
    forward: defaultdict[str, set[str]] = defaultdict(set)
    for e in model.get("flow_edges") or []:
        s = str(e.get("source_path_digest")); t = str(e.get("target_path_digest"))
        if s and t:
            forward[s].add(t)
            reverse[t].add(s)

    direct = {digest_by_path[p] for p in known}
    affected = set(direct)
    depth_by_digest = {d: 0 for d in direct}
    q = deque(direct)
    while q:
        cur = q.popleft()
        depth = depth_by_digest[cur]
        if depth >= MAX_DATAFLOW_DEPTH:
            continue
        for caller in sorted(reverse.get(cur, ())):
            if caller not in affected:
                affected.add(caller)
                depth_by_digest[caller] = depth + 1
                q.append(caller)

    # Coverage candidates are heuristic unless actually executed.
    symbols = {str(x.get("symbol_id")): x for x in sg.get("symbols") or []}
    candidate_tests: set[str] = set()
    for c in sg.get("coverage_link_candidates") or []:
        sym = symbols.get(str(c.get("symbol_id")))
        if sym and str(sym.get("relative_path_digest")) in affected:
            candidate_tests.add(str(c.get("test_file_digest")))
    # Add explicit test files that import or depend on affected files.
    for d in affected:
        for caller in reverse.get(d, ()):
            p = path_by_digest.get(caller, "")
            if p and bool(by_path.get(p, {}).get("test")):
                candidate_tests.add(caller)

    categories = Counter()
    affected_rows: list[dict[str, Any]] = []
    for d in sorted(affected):
        rel = path_by_digest.get(d, "")
        f = by_path.get(rel, {})
        kind = _kind_for_file(rel, is_test=bool(f.get("test"))) if rel else "unknown"
        categories[kind] += 1
        affected_rows.append({
            "relative_path": rel,
            "relative_path_digest": d,
            "impact_depth": int(depth_by_digest.get(d, 0)),
            "kind": kind,
            "confidence": "high" if d in direct else "medium",
        })

    uncertainty: list[dict[str, Any]] = []
    if unknown:
        uncertainty.append(_public_issue("unknown_changed_paths", "high", [digest(x) for x in unknown], "Resolve unknown paths before treating impact analysis as complete."))
    if invalid:
        uncertainty.append(_public_issue("invalid_changed_paths", "high", invalid, "Reject absolute and parent-traversal paths; use repository-relative paths."))
    if int(sg.get("degraded_parser_count") or 0):
        uncertainty.append(_public_issue("degraded_parser", "medium", int(sg.get("degraded_parser_count") or 0), "Treat symbol-derived test selection as incomplete."))
    unresolved = int(model.get("unresolved_dependency_edge_count") or 0)
    if unresolved:
        uncertainty.append(_public_issue("unresolved_dependencies", "medium", unresolved, "Preserve missing edges as uncertainty rather than inventing callers."))
    if any(_is_privateish(p) for p in requested):
        uncertainty.append(_public_issue("private_or_secret_path_requested", "high", [digest(p) for p in requested if _is_privateish(p)], "Do not expose or infer private content from sensitive paths."))

    analysis_id = "deep-impact-" + digest({"workspace": wid, "manifest": pub_model.get("source_manifest_digest"), "requested": requested})[:24]
    row = seal({
        "contract_version": CONTRACT_VERSION,
        "analysis_id": analysis_id,
        "workspace_digest": wid,
        "source_manifest_digest": pub_model.get("source_manifest_digest"),
        "requested_paths": requested,
        "requested_path_digests": [digest(p) for p in requested],
        "known_paths": known,
        "unknown_path_digests": [digest(p) for p in unknown],
        "invalid_path_digests": invalid,
        "affected": affected_rows,
        "candidate_test_path_digests": sorted(candidate_tests),
        "impact_kind_counts": dict(sorted(categories.items())),
        "uncertainty": uncertainty,
        "complete": not uncertainty,
        "tests_executed": False,
        "source_modified": False,
        "provider_contacted": False,
        "live_runtime_verified": False,
        "predictions_not_proof": True,
        "action_executed": False,
        **DENIED_AUTHORITY,
    })
    atomic_json(_impact_path(analysis_id, runtime_root), row)
    return {"ok": not any(x.get("severity") == "high" for x in uncertainty), "status": "deep_impact_ready" if not uncertainty else "deep_impact_uncertain", "impact_analysis": public_change_impact(row), "action_executed": False, **DENIED_AUTHORITY}


def public_change_impact(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "analysis_id": row.get("analysis_id"),
        "workspace_digest": row.get("workspace_digest"),
        "source_manifest_digest": row.get("source_manifest_digest"),
        "requested_path_count": len(row.get("requested_paths") or []),
        "known_path_count": len(row.get("known_paths") or []),
        "unknown_path_count": len(row.get("unknown_path_digests") or []),
        "invalid_path_count": len(row.get("invalid_path_digests") or []),
        "affected_path_count": len(row.get("affected") or []),
        "candidate_test_count": len(row.get("candidate_test_path_digests") or []),
        "impact_kind_counts": dict(row.get("impact_kind_counts") or {}),
        "uncertainty_count": len(row.get("uncertainty") or []),
        "uncertainty": list(row.get("uncertainty") or [])[:MAX_PUBLIC_ISSUES],
        "complete": bool(row.get("complete")),
        "predictions_not_proof": True,
        "tests_executed": False,
        "raw_source_content_exposed": False,
        "source_paths_exposed": False,
        "read_only": True,
        "action_executed": False,
        **DENIED_AUTHORITY,
    }


def load_change_impact_reasoning(analysis_id: str, *, runtime_root=None, include_private: bool = False) -> dict[str, Any]:
    row = read_json(_impact_path(str(analysis_id), runtime_root))
    if not row or not valid(row):
        return {}
    return row if include_private else public_change_impact(row)


def run_portable_unfamiliar_project_benchmark(projects: Iterable[dict[str, Any]], *, runtime_root=None) -> dict[str, Any]:
    """Score held-out project fixtures without claiming Windows/native execution.

    Each project item may contain: name, root, changed_paths, expected_minimums.
    Paths/names are retained only in private external-runtime evidence; public output
    exposes counts and digests.
    """
    project_rows: list[dict[str, Any]] = []
    total_score = 0.0
    total_weight = 0.0
    for item in projects or []:
        root = Path(item.get("root") or "").resolve()
        name = str(item.get("name") or root.name or "project")
        if not root.exists() or not root.is_dir():
            project_rows.append({"project_name": name, "project_digest": digest(name), "status": "missing_project", "score": 0.0, "weight": 1.0})
            total_weight += 1.0
            continue
        before = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}
        model = build_deep_repository_model(root, runtime_root=runtime_root)["repository_model"]
        impact = build_change_impact_reasoning(root, item.get("changed_paths") or [], runtime_root=runtime_root)["impact_analysis"]
        after = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}
        expected = dict(item.get("expected_minimums") or {})
        checks = {
            "source_immutable": before == after,
            "file_count": int(model.get("file_count") or 0) >= int(expected.get("file_count", 1)),
            "module_count": int(model.get("module_count") or 0) >= int(expected.get("module_count", 1)),
            "entry_points": int(model.get("entry_point_candidate_count") or 0) >= int(expected.get("entry_points", 0)),
            "impact_paths": int(impact.get("affected_path_count") or 0) >= int(expected.get("affected_paths", 0)),
            "test_selection": int(impact.get("candidate_test_count") or 0) >= int(expected.get("candidate_tests", 0)),
            "path_privacy": not bool(model.get("source_paths_exposed")) and not bool(impact.get("source_paths_exposed")),
            "authority_preserved": not bool(model.get("action_executed")) and not bool(model.get("standing_authority_granted")) and not bool(impact.get("action_executed")),
        }
        score = sum(1 for v in checks.values() if v) / len(checks)
        weight = float(expected.get("weight", 1.0))
        total_score += score * weight
        total_weight += weight
        project_rows.append({
            "project_name": name,
            "project_digest": digest({"name": name, "manifest": model.get("source_manifest_digest")}),
            "status": "portable_benchmark_ready",
            "score": round(score, 6),
            "weight": weight,
            "checks": checks,
            "repository_model_digest": digest(model),
            "impact_analysis_digest": digest(impact),
            "native_windows_verified": False,
        })

    aggregate = round(total_score / total_weight, 6) if total_weight else 0.0
    bid = "unfamiliar-project-" + digest([(x.get("project_digest"), x.get("score")) for x in project_rows])[:24]
    row = seal({
        "contract_version": CONTRACT_VERSION,
        "benchmark_id": bid,
        "project_count": len(project_rows),
        "aggregate_score": aggregate,
        "projects": project_rows,
        "portable_only": True,
        "native_windows_verified": False,
        "operator_trial_completed": False,
        "source_modified": False,
        "provider_contacted": False,
        "action_executed": False,
        **DENIED_AUTHORITY,
    })
    atomic_json(_benchmark_path(bid, runtime_root), row)
    return {"ok": bool(project_rows) and all(x.get("status") == "portable_benchmark_ready" and x.get("score", 0) >= 0.75 for x in project_rows), "status": "portable_unfamiliar_project_benchmark_ready", "benchmark": public_benchmark(row), "action_executed": False, **DENIED_AUTHORITY}


def public_benchmark(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "benchmark_id": row.get("benchmark_id"),
        "project_count": int(row.get("project_count") or 0),
        "aggregate_score": float(row.get("aggregate_score") or 0.0),
        "project_scores": [{"project_digest": x.get("project_digest"), "score": x.get("score"), "status": x.get("status")} for x in row.get("projects") or []],
        "portable_only": True,
        "native_windows_verified": False,
        "operator_trial_completed": False,
        "raw_source_content_exposed": False,
        "source_paths_exposed": False,
        "read_only": True,
        "action_executed": False,
        **DENIED_AUTHORITY,
    }


def process_deep_project_understanding_control(text: str, *, project_root=None, runtime_root=None) -> dict[str, Any]:
    """Small read-only operator surface; no command here can grant mutation authority."""
    raw = str(text or "").strip()
    low = raw.lower()
    if low in {"inspect deep project understanding", "show deep project understanding", "inspect repository model"}:
        if not project_root:
            return {"active": True, "ok": False, "status": "project_root_required", "action_executed": False, **DENIED_AUTHORITY}
        return {"active": True, **build_deep_repository_model(project_root, runtime_root=runtime_root)}
    prefix = "analyze deep impact:"
    if low.startswith(prefix):
        if not project_root:
            return {"active": True, "ok": False, "status": "project_root_required", "action_executed": False, **DENIED_AUTHORITY}
        paths = [x.strip() for x in raw[len(prefix):].split(",") if x.strip()]
        if not paths:
            return {"active": True, "ok": False, "status": "changed_paths_required", "action_executed": False, **DENIED_AUTHORITY}
        return {"active": True, **build_change_impact_reasoning(project_root, paths, runtime_root=runtime_root)}
    # Explicitly reject mutation language that tries to smuggle execution into inspection.
    if any(phrase in low for phrase in ("and install", "and apply", "and modify", "and delete", "and run it")) and ("project understanding" in low or "impact" in low):
        return {"active": True, "ok": False, "status": "read_only_scope_expansion_rejected", "guidance": "Run project understanding separately from any governed execution request.", "action_executed": False, **DENIED_AUTHORITY}
    return {"active": False}


__all__ = [
    "CONTRACT_VERSION",
    "build_deep_repository_model",
    "public_repository_model",
    "load_deep_repository_model",
    "assess_repository_model_freshness",
    "build_change_impact_reasoning",
    "public_change_impact",
    "load_change_impact_reasoning",
    "run_portable_unfamiliar_project_benchmark",
    "public_benchmark",
    "process_deep_project_understanding_control",
]
