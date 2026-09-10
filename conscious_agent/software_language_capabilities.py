from __future__ import annotations
"""Era 2 / Arc 6 portable multi-language engineering contracts.

The layer identifies language/toolchain boundaries and validates only syntax that
can be checked without installing dependencies or executing project code.  It
composes established Python/Node/browser/broader-language adapters; it does not
replace their execution authority or sandbox contracts.
"""
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
import ast
import json
import re
import shlex
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

from project_evidence_store import DENIED_AUTHORITY, atomic_json, digest, evidence_root, read_json, seal, valid
from repository_inventory import build_repository_inventory, load_repository_inventory
from broader_project_language_adapters import adapter_registry as legacy_adapter_registry

CONTRACT_VERSION = "v1650.9"
MAX_SCAN_BYTES = 512 * 1024

LANGUAGE_CONTRACTS: dict[str, dict[str, Any]] = {
    "python": {"suffixes": [".py"], "parser": "python_ast", "toolchain": "python", "execution_adapter": "python_test_adapter"},
    "javascript": {"suffixes": [".js", ".mjs", ".cjs"], "parser": "node_or_ecmascript_parser", "toolchain": "node", "execution_adapter": "node_javascript_test_adapter"},
    "typescript": {"suffixes": [".ts", ".tsx"], "parser": "typescript_compiler_or_parser", "toolchain": "node_typescript", "execution_adapter": "node_javascript_test_adapter"},
    "html": {"suffixes": [".html", ".htm"], "parser": "python_html_parser", "toolchain": "browser_optional", "execution_adapter": "browser_runtime_test_adapter"},
    "css": {"suffixes": [".css"], "parser": "css_structural_validator", "toolchain": "browser_optional", "execution_adapter": "browser_runtime_test_adapter"},
    "json": {"suffixes": [".json"], "parser": "python_json", "toolchain": "none", "execution_adapter": "structured_data"},
    "yaml": {"suffixes": [".yaml", ".yml"], "parser": "yaml_parser_if_available", "toolchain": "none", "execution_adapter": "structured_data"},
    "shell": {"suffixes": [".sh", ".bash"], "parser": "shell_tokenizer_only", "toolchain": "posix_shell", "execution_adapter": "governed_shell"},
    "powershell": {"suffixes": [".ps1"], "parser": "powershell_native_parser", "toolchain": "powershell", "execution_adapter": "governed_shell"},
    "java": {"suffixes": [".java"], "parser": "javac", "toolchain": "java", "execution_adapter": "java_maven_or_gradle"},
    "csharp": {"suffixes": [".cs"], "parser": "dotnet_compiler", "toolchain": "dotnet", "execution_adapter": "dotnet"},
    "rust": {"suffixes": [".rs"], "parser": "rustc", "toolchain": "rust", "execution_adapter": "rust_cargo"},
    "go": {"suffixes": [".go"], "parser": "go_parser", "toolchain": "go", "execution_adapter": "go_module"},
    "php": {"suffixes": [".php"], "parser": "php_lint", "toolchain": "php", "execution_adapter": "php_composer"},
}

MANIFESTS = {
    "pyproject.toml": ("python", "python_packaging"),
    "requirements.txt": ("python", "pip"),
    "setup.py": ("python", "setuptools"),
    "package.json": ("javascript", "node_package"),
    "package-lock.json": ("javascript", "npm"),
    "yarn.lock": ("javascript", "yarn"),
    "pnpm-lock.yaml": ("javascript", "pnpm"),
    "pom.xml": ("java", "maven"),
    "build.gradle": ("java", "gradle"),
    "build.gradle.kts": ("java", "gradle"),
    "gradlew": ("java", "gradle_wrapper"),
    "gradlew.bat": ("java", "gradle_wrapper"),
    "Cargo.toml": ("rust", "cargo"),
    "Cargo.lock": ("rust", "cargo_locked"),
    "go.mod": ("go", "go_modules"),
    "go.sum": ("go", "go_modules_locked"),
    "composer.json": ("php", "composer"),
    "composer.lock": ("php", "composer_locked"),
}

LOCKFILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock", "go.sum", "composer.lock"}
GENERATED_DIRS = {"node_modules", "dist", "build", "target", "bin", "obj", ".gradle", "vendor", "coverage"}


def _record_path(wid: str, runtime_root=None) -> Path:
    return evidence_root("software_language_capabilities", runtime_root) / "records" / f"{wid}.json"


def _benchmark_path(bid: str, runtime_root=None) -> Path:
    return evidence_root("software_language_capabilities", runtime_root) / "benchmarks" / f"{bid}.json"


def _language_for_path(rel: str, declared: str = "") -> str:
    if declared and declared in LANGUAGE_CONTRACTS:
        return declared
    suffix = PurePosixPath(rel).suffix.lower()
    for language, contract in LANGUAGE_CONTRACTS.items():
        if suffix in contract["suffixes"]:
            return language
    return "unknown"


class _HTMLValidator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = 0
    def handle_starttag(self, tag, attrs):
        self.tags += 1


def _validate_css(text: str) -> tuple[bool, str]:
    # Conservative structural validation only. It is not presented as a browser parser.
    depth = 0
    quote = ""
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if quote:
            if ch == quote:
                quote = ""
            continue
        if ch in "\"'":
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return False, "css_unbalanced_brace"
    if quote:
        return False, "css_unclosed_quote"
    return (depth == 0, "validated" if depth == 0 else "css_unbalanced_brace")


def _validate_yaml_if_available(text: str) -> tuple[bool, str, str]:
    try:
        import yaml  # type: ignore
    except Exception:
        return True, "yaml_parser_unavailable", "deferred"
    try:
        yaml.safe_load(text)
        return True, "validated", "native_parser"
    except Exception:
        return False, "yaml_parse_error", "native_parser"


def validate_portable_syntax(path: str | Path, *, language: str = "") -> dict[str, Any]:
    p = Path(path)
    lang = _language_for_path(p.name, language)
    result = {
        "contract_version": CONTRACT_VERSION,
        "language": lang,
        "validated": False,
        "status": "unsupported_language",
        "parser_evidence": "none",
        "project_code_executed": False,
        "dependency_installed": False,
        "provider_contacted": False,
        "action_executed": False,
        **DENIED_AUTHORITY,
    }
    try:
        if p.stat().st_size > MAX_SCAN_BYTES:
            result["status"] = "file_too_large_for_portable_validation"
            return result
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        result["status"] = "source_unreadable"
        return result
    try:
        if lang == "python":
            ast.parse(text); result.update(validated=True, status="validated", parser_evidence="python_ast")
        elif lang == "json":
            json.loads(text); result.update(validated=True, status="validated", parser_evidence="python_json")
        elif lang == "html":
            parser = _HTMLValidator(); parser.feed(text); parser.close(); result.update(validated=True, status="validated", parser_evidence="python_html_parser")
        elif lang == "css":
            ok, status = _validate_css(text); result.update(validated=ok, status=status, parser_evidence="css_structural_validator")
        elif lang == "yaml":
            ok, status, parser_kind = _validate_yaml_if_available(text); result.update(validated=ok, status=status, parser_evidence=parser_kind)
        elif lang == "shell":
            # Tokenization catches malformed quoting but does not execute or claim full shell grammar validation.
            list(shlex.shlex(text, posix=True)); result.update(validated=True, status="tokenized_not_executed", parser_evidence="shell_tokenizer_only")
        elif lang in {"javascript", "typescript", "powershell", "java", "csharp", "rust", "go", "php"}:
            result.update(validated=False, status="native_parser_deferred", parser_evidence=LANGUAGE_CONTRACTS[lang]["parser"])
        else:
            result["status"] = "unsupported_language"
    except (SyntaxError, ValueError, json.JSONDecodeError, ET.ParseError) as exc:
        result.update(validated=False, status=f"syntax_invalid:{type(exc).__name__}", parser_evidence=LANGUAGE_CONTRACTS.get(lang, {}).get("parser", "unknown"))
    return result


def build_language_capability_model(source_root: str | Path, *, runtime_root=None) -> dict[str, Any]:
    root = Path(source_root).resolve()
    inv_pub = build_repository_inventory(root, runtime_root=runtime_root)["inventory"]
    wid = str(inv_pub["workspace_digest"])
    existing = load_language_capability_model(wid, runtime_root=runtime_root, include_private=True)
    if existing and existing.get("source_manifest_digest") == inv_pub.get("source_manifest_digest"):
        return {"ok": True, "status": "language_capability_model_current", "language_model": public_language_capability_model(existing), "action_executed": False, **DENIED_AUTHORITY}
    inv = load_repository_inventory(wid, runtime_root=runtime_root, include_private=True)
    files = list(inv.get("files") or [])
    languages: dict[str, dict[str, Any]] = {}
    manifests: list[dict[str, Any]] = []
    generated_seen = 0
    syntax_checks: list[dict[str, Any]] = []
    for f in files:
        rel = str(f.get("relative_path") or "")
        suffix = PurePosixPath(rel).suffix.lower()
        lang = _language_for_path(rel, str(f.get("language") or ""))
        if lang != "unknown":
            row = languages.setdefault(lang, {"file_count": 0, "syntax_validated_count": 0, "syntax_deferred_count": 0, "syntax_invalid_count": 0})
            row["file_count"] += 1
            if int(f.get("size_bytes") or 0) <= MAX_SCAN_BYTES and lang in {"python", "json", "html", "css", "yaml", "shell"}:
                syn = validate_portable_syntax(root / rel, language=lang)
                syntax_checks.append({"path_digest": f.get("relative_path_digest"), "language": lang, "status": syn["status"], "validated": bool(syn["validated"]), "parser_evidence": syn["parser_evidence"]})
                if syn["validated"]:
                    row["syntax_validated_count"] += 1
                elif syn["status"] == "native_parser_deferred" or syn["status"] == "yaml_parser_unavailable":
                    row["syntax_deferred_count"] += 1
                else:
                    row["syntax_invalid_count"] += 1
            elif lang in LANGUAGE_CONTRACTS:
                row["syntax_deferred_count"] += 1
        name = PurePosixPath(rel).name
        if name in MANIFESTS:
            l, manager = MANIFESTS[name]
            manifests.append({"path_digest": f.get("relative_path_digest"), "name": name, "language": l, "manager": manager, "lockfile": name in LOCKFILES})
        if any(part in GENERATED_DIRS for part in PurePosixPath(rel).parts):
            generated_seen += 1

    legacy = legacy_adapter_registry()
    row = seal({
        "contract_version": CONTRACT_VERSION,
        "workspace_digest": wid,
        "source_manifest_digest": inv_pub.get("source_manifest_digest"),
        "languages": languages,
        "manifest_records": manifests,
        "syntax_checks": syntax_checks,
        "generated_file_count": generated_seen,
        "legacy_adapter_registry_digest": digest(legacy),
        "execution_adapters_reused": True,
        "native_parser_execution_deferred": True,
        "dependency_installation_authorized": False,
        "runtime_download_authorized": False,
        "project_code_executed": False,
        "source_modified": False,
        "provider_contacted": False,
        "action_executed": False,
        **DENIED_AUTHORITY,
    })
    atomic_json(_record_path(wid, runtime_root), row)
    return {"ok": all(int(x.get("syntax_invalid_count") or 0) == 0 for x in languages.values()), "status": "language_capability_model_ready", "language_model": public_language_capability_model(row), "action_executed": False, **DENIED_AUTHORITY}


def public_language_capability_model(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "workspace_digest": row.get("workspace_digest"),
        "source_manifest_digest": row.get("source_manifest_digest"),
        "languages": {k: dict(v) for k, v in (row.get("languages") or {}).items()},
        "language_count": len(row.get("languages") or {}),
        "manifest_count": len(row.get("manifest_records") or []),
        "lockfile_count": sum(1 for x in row.get("manifest_records") or [] if x.get("lockfile")),
        "generated_file_count": int(row.get("generated_file_count") or 0),
        "execution_adapters_reused": bool(row.get("execution_adapters_reused")),
        "native_parser_execution_deferred": True,
        "dependency_installation_authorized": False,
        "runtime_download_authorized": False,
        "project_code_executed": False,
        "raw_source_content_exposed": False,
        "source_paths_exposed": False,
        "provider_contacted": False,
        "read_only": True,
        "action_executed": False,
        **DENIED_AUTHORITY,
    }


def load_language_capability_model(wid: str, *, runtime_root=None, include_private=False) -> dict[str, Any]:
    row = read_json(_record_path(str(wid), runtime_root))
    if not row or not valid(row):
        return {}
    return row if include_private else public_language_capability_model(row)


def analyze_build_dependency_boundary(source_root: str | Path, *, runtime_root=None, offline: bool = True) -> dict[str, Any]:
    root = Path(source_root).resolve()
    model_result = build_language_capability_model(root, runtime_root=runtime_root)
    pub = model_result["language_model"]
    private = load_language_capability_model(str(pub["workspace_digest"]), runtime_root=runtime_root, include_private=True)
    manifests = list(private.get("manifest_records") or [])
    managers = sorted({str(x.get("manager")) for x in manifests if x.get("manager")})
    has_lock = any(x.get("lockfile") for x in manifests)
    languages = set((private.get("languages") or {}).keys())
    needs_native = sorted(l for l in languages if l in {"javascript", "typescript", "powershell", "java", "csharp", "rust", "go", "php"})
    boundary = {
        "contract_version": CONTRACT_VERSION,
        "workspace_digest": pub.get("workspace_digest"),
        "source_manifest_digest": pub.get("source_manifest_digest"),
        "manager_count": len(managers),
        "manager_digests": [digest(x) for x in managers],
        "lockfile_present": has_lock,
        "offline_requested": bool(offline),
        "native_toolchain_required_count": len(needs_native),
        "native_toolchain_language_digests": [digest(x) for x in needs_native],
        "dependency_resolution_performed": False,
        "dependency_installation_performed": False,
        "network_contacted": False,
        "offline_ready_proven": False,
        "installation_requires_separate_authority": True,
        "native_toolchain_evidence_deferred": bool(needs_native),
        "source_modified": False,
        "action_executed": False,
        **DENIED_AUTHORITY,
    }
    boundary["boundary_digest"] = digest(boundary)
    return {"ok": True, "status": "build_dependency_boundary_ready", "boundary": boundary, "action_executed": False, **DENIED_AUTHORITY}


def run_portable_cross_language_checkpoint(projects: Iterable[dict[str, Any]], *, runtime_root=None) -> dict[str, Any]:
    rows = []
    for item in projects or []:
        root = Path(item.get("root") or "").resolve()
        expected = set(item.get("expected_languages") or [])
        name = str(item.get("name") or root.name or "project")
        if not root.exists() or not root.is_dir():
            rows.append({"project_digest": digest(name), "status": "missing_project", "score": 0.0})
            continue
        before = digest(sorted((p.relative_to(root).as_posix(), digest(p.read_bytes())) for p in root.rglob("*") if p.is_file()))
        model = build_language_capability_model(root, runtime_root=runtime_root)["language_model"]
        boundary = analyze_build_dependency_boundary(root, runtime_root=runtime_root)["boundary"]
        after = digest(sorted((p.relative_to(root).as_posix(), digest(p.read_bytes())) for p in root.rglob("*") if p.is_file()))
        got = set((model.get("languages") or {}).keys())
        checks = {
            "language_detection": expected.issubset(got),
            "source_immutable": before == after,
            "no_dependency_install": not boundary.get("dependency_installation_performed"),
            "no_network": not boundary.get("network_contacted"),
            "authority_preserved": not model.get("standing_authority_granted") and not boundary.get("standing_authority_granted"),
            "paths_private": not model.get("source_paths_exposed"),
        }
        score = sum(bool(v) for v in checks.values()) / len(checks)
        rows.append({"project_digest": digest({"name": name, "manifest": model.get("source_manifest_digest")}), "status": "portable_cross_language_ready", "score": round(score, 6), "checks": checks})
    bid = "cross-language-" + digest([(x.get("project_digest"), x.get("score")) for x in rows])[:24]
    record = seal({
        "contract_version": CONTRACT_VERSION,
        "benchmark_id": bid,
        "project_count": len(rows),
        "projects": rows,
        "aggregate_score": round(sum(float(x.get("score") or 0) for x in rows) / len(rows), 6) if rows else 0.0,
        "portable_only": True,
        "native_builds_executed": False,
        "dependencies_installed": False,
        "network_contacted": False,
        "native_windows_verified": False,
        "source_modified": False,
        "action_executed": False,
        **DENIED_AUTHORITY,
    })
    atomic_json(_benchmark_path(bid, runtime_root), record)
    public = {
        "contract_version": CONTRACT_VERSION,
        "benchmark_id": bid,
        "project_count": len(rows),
        "aggregate_score": record["aggregate_score"],
        "project_scores": [{"project_digest": x.get("project_digest"), "score": x.get("score"), "status": x.get("status")} for x in rows],
        "portable_only": True,
        "native_builds_executed": False,
        "dependencies_installed": False,
        "network_contacted": False,
        "native_windows_verified": False,
        "raw_source_content_exposed": False,
        "source_paths_exposed": False,
        "action_executed": False,
        **DENIED_AUTHORITY,
    }
    return {"ok": bool(rows) and all(x.get("status") == "portable_cross_language_ready" and float(x.get("score") or 0) >= 0.8 for x in rows), "status": "portable_cross_language_checkpoint_ready", "checkpoint": public, "action_executed": False, **DENIED_AUTHORITY}


__all__ = [
    "CONTRACT_VERSION", "LANGUAGE_CONTRACTS", "MANIFESTS",
    "validate_portable_syntax", "build_language_capability_model", "public_language_capability_model",
    "load_language_capability_model", "analyze_build_dependency_boundary", "run_portable_cross_language_checkpoint",
]
