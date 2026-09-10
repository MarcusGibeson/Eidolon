from __future__ import annotations

"""v1258.3-v1258.5 complete application construction integration.

This module evaluates a generated isolated workspace as one application rather
than as independent syntax-valid files.  It checks artifact-role coverage,
cross-file references, dependency/configuration coherence, project-owned tests,
documentation, and (for web applications) structural accessibility and
responsive behavior.  The checks are deterministic and content-minimized.

Execution still belongs to the existing v1254 isolated coding authorization;
this module adds no provider, apply, install, or release authority.
"""

import json
import re
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from complete_application_construction_foundations import (
    DENIED_AUTHORITY,
    load_complete_application_construction,
    prepare_complete_application_construction,
    public_complete_application_construction,
)
from isolated_coding_execution_foundations import check_coding_source_freshness, load_coding_work_request
from ordinary_chat_development_campaign import _atomic_json, _digest, _proposal_lock, _read_json, _store_root

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1258.5"
MAX_QUALITY_FINDINGS = 24
MAX_FILE_READ_BYTES = 256 * 1024


def _quality_path(request_id: str, attempt_number: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "complete_application_quality" / request_id / f"attempt-{int(attempt_number)}.json"


def _seal(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({k: v for k, v in row.items() if k != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({k: v for k, v in record.items() if k != field}))


def _failure(status: str, request_id: str, attempt_number: int = 0) -> dict[str, Any]:
    row = {
        "ok": False,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "request_id": request_id,
        "attempt_number": int(attempt_number),
        "passed": False,
        "content_minimized": True,
        "raw_file_contents_stored": False,
        "selected_project_modified": False,
        "source_modified": False,
        **DENIED_AUTHORITY,
    }
    row["failure_digest"] = _digest(row)
    return row


def _workspace_root(request_id: str, runtime_root=None) -> Path | None:
    row = _read_json(_store_root(runtime_root) / "coding_workspace_records" / f"{request_id}.json")
    if not row:
        return None
    root = Path(str(row.get("workspace_path") or ""))
    try:
        resolved = root.resolve(strict=True)
    except OSError:
        return None
    return resolved if resolved.is_dir() and not resolved.is_symlink() else None


def _files(root: Path) -> list[str]:
    rows: list[str] = []
    for path in sorted(root.rglob("*"), key=lambda p: p.as_posix().casefold()):
        if path.is_symlink():
            raise ValueError("workspace_link_detected")
        if not path.is_file():
            continue
        resolved = path.resolve(strict=True)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError("workspace_boundary_escape") from exc
        rel = path.relative_to(root).as_posix()
        rows.append(rel)
    folded = [row.casefold() for row in rows]
    if len(folded) != len(set(folded)):
        raise ValueError("workspace_casefold_collision")
    return rows


def _read(root: Path, relative: str) -> str:
    path = root / Path(*PurePosixPath(relative).parts)
    if not path.is_file() or path.is_symlink():
        return ""
    data = path.read_bytes()
    if len(data) > MAX_FILE_READ_BYTES:
        raise ValueError("quality_file_read_budget_exceeded")
    return data.decode("utf-8")


def _is_test(path: str) -> bool:
    pure = PurePosixPath(path)
    name = pure.name.casefold()
    parts = {part.casefold() for part in pure.parts[:-1]}
    return name.startswith("test_") or name.endswith(("_test.py", ".test.js", ".spec.js", ".test.mjs", ".spec.mjs")) or bool(parts & {"test", "tests"})


def _find(files: Sequence[str], names: Sequence[str]) -> str:
    wanted = {name.casefold() for name in names}
    return next((path for path in files if PurePosixPath(path).name.casefold() in wanted), "")


def _finding(code: str, dimension: str, passed: bool, *, evidence: Sequence[str] = ()) -> dict[str, Any]:
    row = {
        "finding_code": code,
        "dimension": dimension,
        "passed": bool(passed),
        "evidence_codes": list(evidence)[:6],
    }
    row["finding_digest"] = _digest(row)
    return row


class _WebStructure(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_lang = False
        self.viewport = False
        self.main = False
        self.script_refs: list[str] = []
        self.style_refs: list[str] = []
        self.ids: set[str] = set()
        self.label_for: set[str] = set()
        self.controls: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {str(k).casefold(): str(v or "") for k, v in attrs}
        tag = tag.casefold()
        if tag == "html" and values.get("lang", "").strip():
            self.html_lang = True
        if tag == "meta" and values.get("name", "").casefold() == "viewport" and values.get("content", "").strip():
            self.viewport = True
        if tag == "main":
            self.main = True
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "label" and values.get("for"):
            self.label_for.add(values["for"])
        if tag == "script" and values.get("src"):
            self.script_refs.append(values["src"])
        if tag == "link" and values.get("rel", "").casefold() == "stylesheet" and values.get("href"):
            self.style_refs.append(values["href"])
        if tag in {"input", "select", "textarea", "button"}:
            self.controls.append({
                "tag": tag,
                "id": values.get("id", ""),
                "aria": values.get("aria-label", "") or values.get("aria-labelledby", ""),
                "type": values.get("type", ""),
            })


def _local_ref(value: str) -> str:
    value = value.split("#", 1)[0].split("?", 1)[0].strip()
    if not value or value.startswith(("http://", "https://", "//", "data:", "mailto:", "javascript:")):
        return ""
    return PurePosixPath(value.lstrip("./")).as_posix()


def _web_findings(root: Path, files: Sequence[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    html_path = _find(files, ["index.html", "index.htm"]) or next((p for p in files if p.endswith((".html", ".htm"))), "")
    css_paths = [p for p in files if p.endswith(".css")]
    js_paths = [p for p in files if PurePosixPath(p).suffix.casefold() in {".js", ".mjs", ".cjs"} and not _is_test(p)]
    test_paths = [p for p in files if _is_test(p)]
    config_path = _find(files, ["package.json"])
    readme_path = _find(files, ["README.md", "README.txt"])

    parser = _WebStructure()
    html = _read(root, html_path) if html_path else ""
    if html:
        try:
            parser.feed(html)
        except Exception:
            pass
    findings.append(_finding("interface_artifact_present", "interface_coherence", bool(html_path), evidence=["html_present" if html_path else "html_missing"]))
    findings.append(_finding("application_logic_artifact_present", "interface_coherence", bool(js_paths), evidence=["js_present" if js_paths else "js_missing"]))
    findings.append(_finding("style_artifact_present", "interface_coherence", bool(css_paths), evidence=["css_present" if css_paths else "css_missing"]))

    all_refs = [("script", ref) for ref in parser.script_refs] + [("style", ref) for ref in parser.style_refs]
    missing_refs: list[str] = []
    for kind, ref in all_refs:
        local = _local_ref(ref)
        if local and local.casefold() not in {p.casefold() for p in files}:
            missing_refs.append(kind)
    linked_script = any(_local_ref(ref).casefold() in {p.casefold() for p in js_paths} for ref in parser.script_refs if _local_ref(ref))
    linked_style = any(_local_ref(ref).casefold() in {p.casefold() for p in css_paths} for ref in parser.style_refs if _local_ref(ref))
    findings.append(_finding("local_interface_references_resolve", "interface_coherence", not missing_refs, evidence=[f"missing_{kind}_reference" for kind in missing_refs]))
    findings.append(_finding("interface_links_application_logic", "interface_coherence", bool(js_paths) and linked_script, evidence=["script_linked" if linked_script else "script_not_linked"]))
    findings.append(_finding("interface_links_styles", "interface_coherence", bool(css_paths) and linked_style, evidence=["styles_linked" if linked_style else "styles_not_linked"]))

    findings.append(_finding("document_language_declared", "accessibility", parser.html_lang, evidence=["html_lang"] if parser.html_lang else ["html_lang_missing"]))
    findings.append(_finding("viewport_declared", "responsive_behavior", parser.viewport, evidence=["viewport"] if parser.viewport else ["viewport_missing"]))
    findings.append(_finding("semantic_main_present", "accessibility", parser.main, evidence=["main_landmark"] if parser.main else ["main_landmark_missing"]))
    inaccessible = [row for row in parser.controls if row["tag"] != "button" and not row["aria"] and (not row["id"] or row["id"] not in parser.label_for)]
    findings.append(_finding("controls_structurally_labelled", "accessibility", not inaccessible, evidence=["labelled_controls" if not inaccessible else "unlabelled_control_present"]))

    css = "\n".join(_read(root, p) for p in css_paths)
    focus = bool(re.search(r":focus(?:-visible)?\b", css, re.I))
    media = "@media" in css.casefold()
    fluid = bool(re.search(r"\b(?:max-width|min-width|width)\s*:\s*(?:min\(|max\(|clamp\(|\d+(?:\.\d+)?(?:%|vw|rem|em))", css, re.I)) or "grid" in css.casefold() or "flex" in css.casefold()
    findings.append(_finding("keyboard_focus_visible", "accessibility", focus, evidence=["focus_rule"] if focus else ["focus_rule_missing"]))
    findings.append(_finding("responsive_breakpoint_present", "responsive_behavior", media, evidence=["media_query"] if media else ["media_query_missing"]))
    findings.append(_finding("fluid_layout_present", "responsive_behavior", fluid, evidence=["fluid_layout"] if fluid else ["fluid_layout_missing"]))

    config_ok = False
    test_command = False
    deps_declared = False
    package = {}
    if config_path:
        try:
            package = json.loads(_read(root, config_path))
            config_ok = isinstance(package, dict)
            scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
            test_command = bool(str(scripts.get("test") or "").strip())
            deps_declared = isinstance(package.get("dependencies", {}), dict) and isinstance(package.get("devDependencies", {}), dict)
        except (ValueError, json.JSONDecodeError):
            pass
    findings.append(_finding("project_configuration_valid", "configuration_coherence", config_ok, evidence=["package_json_valid" if config_ok else "package_json_missing_or_invalid"]))
    findings.append(_finding("test_command_declared", "configuration_coherence", test_command, evidence=["test_script"] if test_command else ["test_script_missing"]))
    findings.append(_finding("dependency_sections_declared", "dependency_coherence", deps_declared, evidence=["dependency_sections"] if deps_declared else ["dependency_sections_missing"]))

    # External bare imports are only coherent if declared. Relative/local imports
    # are handled by workspace/path containment elsewhere.
    bare_imports: set[str] = set()
    for path in js_paths:
        content = _read(root, path)
        for match in re.finditer(r"(?:from\s+|import\s*\(\s*|require\s*\(\s*)['\"]([^'\"./][^'\"]*)['\"]", content):
            bare_imports.add(match.group(1).split("/", 1)[0])
    declared = set()
    if isinstance(package, dict):
        declared.update(str(k) for k in (package.get("dependencies") or {}))
        declared.update(str(k) for k in (package.get("devDependencies") or {}))
    undeclared = sorted(dep for dep in bare_imports if dep not in declared)
    findings.append(_finding("external_dependencies_declared", "dependency_coherence", not undeclared, evidence=["no_undeclared_external_dependency"] if not undeclared else ["undeclared_external_dependency"]))

    findings.append(_finding("project_owned_tests_present", "test_coverage", bool(test_paths), evidence=["test_files_present" if test_paths else "test_files_missing"]))
    readme = _read(root, readme_path).casefold() if readme_path else ""
    run_guidance = bool(re.search(r"\b(run|start|open|serve|launch)\b", readme))
    test_guidance = "test" in readme
    findings.append(_finding("documentation_present", "documentation_completeness", bool(readme_path), evidence=["readme_present" if readme_path else "readme_missing"]))
    findings.append(_finding("documentation_run_guidance", "documentation_completeness", run_guidance, evidence=["run_guidance" if run_guidance else "run_guidance_missing"]))
    findings.append(_finding("documentation_test_guidance", "documentation_completeness", test_guidance, evidence=["test_guidance" if test_guidance else "test_guidance_missing"]))
    summary = {
        "interface_path_digest": _digest(html_path) if html_path else "",
        "logic_file_count": len(js_paths),
        "style_file_count": len(css_paths),
        "test_file_count": len(test_paths),
        "configuration_present": bool(config_path),
        "documentation_present": bool(readme_path),
        "local_reference_count": len(all_refs),
        "external_dependency_count": len(bare_imports),
        "undeclared_external_dependency_count": len(undeclared),
    }
    return findings, summary


def _python_findings(root: Path, files: Sequence[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sources = [p for p in files if p.endswith(".py") and not _is_test(p)]
    tests = [p for p in files if p.endswith(".py") and _is_test(p)]
    config = _find(files, ["pyproject.toml", "requirements.txt", "setup.cfg", "setup.py"])
    readme = _find(files, ["README.md", "README.txt"])
    readme_text = _read(root, readme).casefold() if readme else ""
    findings = [
        _finding("application_logic_artifact_present", "interface_coherence", bool(sources), evidence=["python_source_present" if sources else "python_source_missing"]),
        _finding("project_configuration_present", "configuration_coherence", bool(config), evidence=["project_config_present" if config else "project_config_missing"]),
        _finding("dependencies_declared_or_explicitly_empty", "dependency_coherence", bool(config), evidence=["dependency_configuration_present" if config else "dependency_configuration_missing"]),
        _finding("project_owned_tests_present", "test_coverage", bool(tests), evidence=["test_files_present" if tests else "test_files_missing"]),
        _finding("documentation_present", "documentation_completeness", bool(readme), evidence=["readme_present" if readme else "readme_missing"]),
        _finding("documentation_run_guidance", "documentation_completeness", bool(re.search(r"\b(run|start|launch|python)\b", readme_text)), evidence=["run_guidance" if readme_text else "run_guidance_missing"]),
        _finding("documentation_test_guidance", "documentation_completeness", "test" in readme_text, evidence=["test_guidance" if "test" in readme_text else "test_guidance_missing"]),
    ]
    return findings, {"source_file_count": len(sources), "test_file_count": len(tests), "configuration_present": bool(config), "documentation_present": bool(readme)}


def _generic_findings(root: Path, files: Sequence[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tests = [p for p in files if _is_test(p)]
    readme = _find(files, ["README.md", "README.txt"])
    findings = [
        _finding("application_artifacts_present", "interface_coherence", bool(files), evidence=["source_files_present" if files else "source_files_missing"]),
        _finding("project_owned_tests_present", "test_coverage", bool(tests), evidence=["test_files_present" if tests else "test_files_missing"]),
        _finding("documentation_present", "documentation_completeness", bool(readme), evidence=["readme_present" if readme else "readme_missing"]),
    ]
    return findings, {"file_count": len(files), "test_file_count": len(tests), "documentation_present": bool(readme)}


def evaluate_complete_application_quality(request_id: str, attempt_number: int, *, runtime_root=None) -> dict[str, Any]:
    request_id = str(request_id or "").lower()
    attempt_number = int(attempt_number)
    contract = load_complete_application_construction(request_id, runtime_root=runtime_root)
    if not contract:
        return _failure("complete_application_construction_contract_missing_or_invalid", request_id, attempt_number)
    request = load_coding_work_request(request_id, runtime_root=runtime_root)
    if not request or request.get("cancelled"):
        return _failure("complete_application_construction_request_cancelled_or_missing", request_id, attempt_number)
    freshness = check_coding_source_freshness(request_id, runtime_root=runtime_root)
    if freshness.get("ok") is not True:
        return _failure("complete_application_construction_stale_source", request_id, attempt_number)
    path = _quality_path(request_id, attempt_number, runtime_root)
    with _proposal_lock(request_id, runtime_root):
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "quality_result_digest"):
                return _failure("complete_application_quality_record_invalid", request_id, attempt_number)
            return {**existing, "operation_status": "restored"}
    root = _workspace_root(request_id, runtime_root)
    if root is None:
        return _failure("complete_application_workspace_missing_or_invalid", request_id, attempt_number)
    try:
        files = _files(root)
        profile = str(contract.get("construction_profile") or "")
        if profile == "web_application":
            findings, summary = _web_findings(root, files)
        elif profile == "python_application":
            findings, summary = _python_findings(root, files)
        else:
            findings, summary = _generic_findings(root, files)
    except (OSError, UnicodeError, ValueError) as exc:
        return _failure(f"complete_application_quality_workspace_rejected:{type(exc).__name__}", request_id, attempt_number)

    findings = findings[:MAX_QUALITY_FINDINGS]
    failed_codes = [str(row.get("finding_code") or "") for row in findings if row.get("passed") is not True]
    dimensions: dict[str, bool] = {}
    for dimension in contract.get("required_quality_dimensions") or []:
        related = [row for row in findings if row.get("dimension") == dimension]
        dimensions[str(dimension)] = bool(related) and all(row.get("passed") is True for row in related)
    passed = not failed_codes and all(dimensions.values())
    record = {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "foundation_contract_version": str(contract.get("contract_version") or ""),
        "status": "complete_application_quality_passed" if passed else "complete_application_quality_failed",
        "request_id": request_id,
        "attempt_number": attempt_number,
        "construction_contract_digest": str(contract.get("construction_contract_digest") or ""),
        "construction_profile": str(contract.get("construction_profile") or ""),
        "passed": passed,
        "finding_count": len(findings),
        "findings": findings,
        "failed_finding_codes": failed_codes,
        "failed_finding_count": len(failed_codes),
        "dimension_results": dimensions,
        "workspace_summary": summary,
        "workspace_file_count": len(files),
        "workspace_manifest_digest": _digest([(p, (root / Path(*PurePosixPath(p).parts)).stat().st_size) for p in files]),
        "content_minimized": True,
        "raw_file_contents_stored": False,
        "private_paths_publicly_exposed": False,
        "selected_project_modified": False,
        "source_modified": False,
        "operator_review_required": True,
        **DENIED_AUTHORITY,
    }
    record = _seal(record, "quality_result_digest")
    with _proposal_lock(request_id, runtime_root):
        prior = _read_json(path)
        if prior:
            if _valid(prior, "quality_result_digest"):
                return {**prior, "operation_status": "restored"}
            return _failure("complete_application_quality_record_invalid", request_id, attempt_number)
        _atomic_json(path, record)
    return {**record, "operation_status": "created"}


def load_complete_application_quality(request_id: str, attempt_number: int, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_quality_path(str(request_id or "").lower(), int(attempt_number), runtime_root))
    return row if row and _valid(row, "quality_result_digest") else {}


def public_complete_application_quality(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(record.get("ok")),
        "status": str(record.get("status") or ""),
        "request_id": str(record.get("request_id") or ""),
        "attempt_number": int(record.get("attempt_number") or 0),
        "construction_profile": str(record.get("construction_profile") or ""),
        "passed": bool(record.get("passed")),
        "failed_finding_codes": list(record.get("failed_finding_codes") or [])[:MAX_QUALITY_FINDINGS],
        "dimension_results": dict(record.get("dimension_results") or {}),
        "workspace_summary": dict(record.get("workspace_summary") or {}),
        "construction_contract_digest": str(record.get("construction_contract_digest") or ""),
        "quality_result_digest": str(record.get("quality_result_digest") or ""),
        "content_minimized": True,
        "raw_file_contents_exposed": False,
        "private_paths_exposed": False,
        "selected_project_modified": False,
        "source_modified": False,
        **DENIED_AUTHORITY,
    }


def prepare_complete_application_execution(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    """Prepare construction + existing v1254 execution without consuming authority."""
    contract = prepare_complete_application_construction(request_id, runtime_root=runtime_root, force=True)
    if contract.get("ok") is not True:
        return contract
    from isolated_coding_execution import prepare_isolated_coding_execution, public_isolated_coding_execution
    execution = prepare_isolated_coding_execution(request_id, runtime_root=runtime_root)
    if execution.get("ok") is not True:
        return execution
    row = {
        "ok": True,
        "status": "complete_application_execution_authorization_required",
        "request_id": request_id,
        "construction": public_complete_application_construction(contract),
        "execution": public_isolated_coding_execution(execution),
        "operator_review_required": True,
        "selected_project_modified": False,
        "source_modified": False,
        **DENIED_AUTHORITY,
    }
    row["preparation_digest"] = _digest(row)
    return row


__all__ = [
    "CONTRACT_VERSION",
    "evaluate_complete_application_quality",
    "load_complete_application_quality",
    "prepare_complete_application_execution",
    "public_complete_application_quality",
]
