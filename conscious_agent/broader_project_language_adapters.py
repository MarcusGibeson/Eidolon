from __future__ import annotations

"""Read-only broader project/language adapter detection and review.

v1238 inspects a sanitized relative-path inventory and manifest digests, selects
or defers a project adapter deterministically, and prepares a content-free
v1237-compatible orchestration blueprint. It never reads file contents, invokes
build tools, installs dependencies, contacts providers, mutates a project, or
grants execution/session authority.
"""

import os
import re
import shutil
import time
from contextlib import contextmanager
from pathlib import PurePosixPath, Path
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root
from multi_tool_orchestration import (
    load_multi_tool_orchestration_plan,
    load_multi_tool_orchestration_review,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1238.8"
MAX_RECORDS = 300
REVIEW_DISPOSITIONS = {"accept_adapter", "hold", "reject", "request_changes"}
DETECTION_STATES = {
    "adapter_selected",
    "adapter_ambiguous",
    "adapter_unsupported",
    "adapter_delegated_existing",
    "adapter_blocked",
}

AUTHORITY_FLAGS = {
    "adapter_detection_authorized": True,
    "adapter_review_authorized": True,
    "orchestration_blueprint_preparation_authorized": True,
    "file_content_read_authorized": False,
    "tool_invocation_authorized": False,
    "provider_execution_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "dependency_installation_authorized": False,
    "runtime_download_authorized": False,
    "workspace_materialization_authorized": False,
    "project_mutation_authorized": False,
    "queue_mutation_authorized": False,
    "schedule_mutation_authorized": False,
    "cognition_write_authorized": False,
    "automatic_continuation_authorized": False,
    "automatic_retry_authorized": False,
    "background_execution_authorized": False,
    "launch_authorized": False,
    "resume_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "old_authority_reusable": False,
}

_HEX64 = re.compile(r"^[a-f0-9]{64}$")
_PROJECT_REF = re.compile(r"^project_[a-f0-9]{16,64}$")
_ASSESSMENT_ID = re.compile(r"^adapter_assessment_[a-f0-9]{24}$")
_REVIEW_ID = re.compile(r"^adapter_review_[a-f0-9]{24}$")
_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9._+@()\- ]{1,128}$")
_SECRET_NAMES = {
    ".env", ".env.local", ".env.production", "id_rsa", "id_ed25519",
    "credentials.json", "secrets.json", "private_key.pem", "service-account.json",
}

_REVIEW = re.compile(
    r"^review broader project adapter (?P<decision>accept_adapter|hold|reject|request_changes) "
    r"for assessment (?P<assessment>adapter_assessment_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_SHOW_ASSESSMENTS = re.compile(r"^show broader project adapter assessments[.!?]*$", re.I)
_SHOW_REVIEWS = re.compile(r"^show broader project adapter reviews[.!?]*$", re.I)
_SHOW_REGISTRY = re.compile(r"^show broader project adapter registry[.!?]*$", re.I)
_SHOW_ASSESSMENT = re.compile(
    r"^show broader project adapter assessment (?P<assessment>adapter_assessment_[a-f0-9]{24})[.!?]*$",
    re.I,
)


def _adapter(
    adapter_id: str,
    display_name: str,
    project_kind: str,
    language: str,
    build_system: str,
    marker_codes: Iterable[str],
    manifests: Iterable[str],
    source_suffixes: Iterable[str],
    generated_directories: Iterable[str],
    runtime_dependencies: Iterable[str],
    build_command: Iterable[str],
    test_command: Iterable[str],
    test_evidence_kind: str,
) -> dict[str, Any]:
    row = {
        "adapter_id": adapter_id,
        "display_name": display_name,
        "project_kind": project_kind,
        "language": language,
        "build_system": build_system,
        "marker_codes": sorted(marker_codes),
        "manifest_names": sorted(manifests),
        "source_suffixes": sorted(source_suffixes),
        "generated_directories": sorted(generated_directories),
        "runtime_dependencies": sorted(runtime_dependencies),
        "build_command_template": list(build_command),
        "test_command_template": list(test_command),
        "test_evidence_kind": test_evidence_kind,
        "runtime_availability": "deferred_until_separately_authorized_execution",
        "command_templates_descriptive_only": True,
        "supports_bounded_build_plan": True,
        "supports_bounded_test_plan": True,
        "installs_dependencies": False,
        "downloads_runtimes": False,
        "executes_commands": False,
    }
    row["adapter_contract_digest"] = _digest(row)
    return row


_ADAPTERS = (
    _adapter(
        "java_maven", "Java Maven Project Adapter", "java_maven_project", "java", "maven",
        ("manifest_pom_xml",), ("pom.xml",), (".java",), ("target",),
        ("java_runtime", "maven_runtime"), ("mvn", "-q", "-DskipTests", "package"),
        ("mvn", "-q", "test"), "maven_surefire_summary",
    ),
    _adapter(
        "java_gradle", "Java Gradle Project Adapter", "java_gradle_project", "java", "gradle",
        ("manifest_gradle_build",), ("build.gradle", "build.gradle.kts"), (".java", ".kt"), ("build", ".gradle"),
        ("java_runtime", "gradle_wrapper_or_runtime"), ("gradle_wrapper", "assemble"),
        ("gradle_wrapper", "test"), "gradle_test_summary",
    ),
    _adapter(
        "dotnet", ".NET Project Adapter", "dotnet_project", "csharp_or_fsharp", "dotnet",
        ("manifest_dotnet_project",), ("*.sln", "*.csproj", "*.fsproj"), (".cs", ".fs", ".vb"), ("bin", "obj"),
        ("dotnet_sdk",), ("dotnet", "build", "--no-restore"),
        ("dotnet", "test", "--no-build"), "dotnet_test_summary",
    ),
    _adapter(
        "rust_cargo", "Rust Cargo Project Adapter", "rust_cargo_project", "rust", "cargo",
        ("manifest_cargo_toml",), ("Cargo.toml",), (".rs",), ("target",),
        ("rust_toolchain", "cargo_runtime"), ("cargo", "check", "--locked"),
        ("cargo", "test", "--locked"), "cargo_test_summary",
    ),
    _adapter(
        "go_module", "Go Module Project Adapter", "go_module_project", "go", "go_modules",
        ("manifest_go_mod",), ("go.mod",), (".go",), ("bin",),
        ("go_runtime",), ("go", "build", "./..."),
        ("go", "test", "./..."), "go_test_summary",
    ),
    _adapter(
        "php_composer", "PHP Composer Project Adapter", "php_composer_project", "php", "composer",
        ("manifest_composer_json",), ("composer.json",), (".php",), ("vendor",),
        ("php_runtime", "composer_runtime"), ("composer", "validate", "--no-check-publish"),
        ("composer_test_script",), "php_test_summary",
    ),
)

_EXISTING_DELEGATIONS = {
    "manifest_package_json": "node_javascript",
    "manifest_pyproject": "python",
    "manifest_setup_py": "python",
    "manifest_requirements": "python",
    "manifest_static_web": "browser_runtime",
}


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root)


def _dir(name: str, runtime_root=None) -> Path:
    return _root(runtime_root) / name


def _path(name: str, record_id: str, runtime_root=None) -> Path:
    return _dir(name, runtime_root) / f"{str(record_id or '').lower()}.json"


@contextmanager
def _lock(runtime_root=None):
    path = _root(runtime_root) / "locks" / "broader-project-language-adapters.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 15.0
    while True:
        try:
            path.mkdir()
            (path / "owner").write_text(str(os.getpid()), encoding="ascii")
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > 60:
                    shutil.rmtree(path, ignore_errors=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for broader project adapter lock")
            time.sleep(0.02)
    try:
        yield
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _sealed(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({key: value for key, value in row.items() if key != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != field}))


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "content_free": True,
        "project_scoped": True,
        "runtime_records_external": True,
        "historical_records_immutable": True,
        "operator_review_required": True,
        "project_contents_read": False,
        "manifest_contents_read": False,
        "commands_executed": False,
        "tests_executed": False,
        "dependencies_installed": False,
        "runtimes_downloaded": False,
        "provider_contacted": False,
        "project_modified": False,
        "queue_modified": False,
        "schedule_modified": False,
        "cognition_written": False,
        "source_modified": False,
        "tool_invoked": False,
        "automatic_continuation_created": False,
        "hidden_retry_created": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_manifest_exposed": False,
        "raw_command_output_exposed": False,
        **AUTHORITY_FLAGS,
    }


def _failure(status: str, reason: str = "") -> dict[str, Any]:
    row = {"ok": False, "status": status, "reason": reason, **_base()}
    row["broader_project_adapter_result_digest"] = _digest(row)
    return row


def adapter_registry() -> dict[str, Any]:
    rows = [dict(row) for row in _ADAPTERS]
    result = {
        "ok": True,
        "status": "broader_project_adapter_registry_ready",
        "adapter_count": len(rows),
        "adapters": rows,
        "existing_adapter_delegations": dict(sorted(_EXISTING_DELEGATIONS.items())),
        "inspection_only": True,
        **_base(),
    }
    result["registry_digest"] = _digest(result)
    return result


def _marker_for_path(path: str) -> str | None:
    lower = path.lower()
    name = PurePosixPath(lower).name
    if name == "pom.xml": return "manifest_pom_xml"
    if name in {"build.gradle", "build.gradle.kts"}: return "manifest_gradle_build"
    if name.endswith((".sln", ".csproj", ".fsproj")): return "manifest_dotnet_project"
    if name == "cargo.toml": return "manifest_cargo_toml"
    if name == "go.mod": return "manifest_go_mod"
    if name == "composer.json": return "manifest_composer_json"
    if name == "package.json": return "manifest_package_json"
    if name == "pyproject.toml": return "manifest_pyproject"
    if name == "setup.py": return "manifest_setup_py"
    if name.startswith("requirements") and name.endswith(".txt"): return "manifest_requirements"
    if name in {"index.html", "index.htm"}: return "manifest_static_web"
    return None


def _normalize_inventory(relative_paths: Iterable[Any], manifest_digests: Mapping[str, Any] | None = None) -> dict[str, Any]:
    paths: list[str] = []
    markers: list[dict[str, str]] = []
    suffixes: set[str] = set()
    parents: set[str] = set()
    seen: set[str] = set()
    for raw in relative_paths or []:
        text = str(raw or "").replace("\\", "/").strip()
        if not text or text.startswith("/") or re.match(r"^[A-Za-z]:", text):
            raise ValueError("absolute_or_empty_path_blocked")
        pure = PurePosixPath(text)
        if any(part in {"", ".", ".."} for part in pure.parts):
            raise ValueError("path_traversal_or_ambiguous_path_blocked")
        if any(not _SAFE_COMPONENT.fullmatch(part) for part in pure.parts):
            raise ValueError("unsafe_path_component_blocked")
        normalized = pure.as_posix()
        if normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        name = pure.name.lower()
        if name in _SECRET_NAMES or name.endswith((".pem", ".p12", ".pfx", ".key")):
            raise ValueError("secret_bearing_filename_blocked")
        paths.append(normalized)
        if pure.suffix:
            suffixes.add(pure.suffix.lower())
        marker = _marker_for_path(normalized)
        if marker:
            parent = pure.parent.as_posix()
            parents.add(parent)
            markers.append({"marker_code": marker, "parent_digest": _digest(parent)})
    if not paths:
        raise ValueError("path_inventory_required")
    supplied = dict(manifest_digests or {})
    normalized_digests: dict[str, str] = {}
    marker_names = {PurePosixPath(path).name.lower() for path in paths if _marker_for_path(path)}
    for name, value in supplied.items():
        key = str(name or "").lower().strip()
        digest = str(value or "").lower().strip()
        if key not in marker_names:
            raise ValueError("manifest_digest_without_inventory_marker")
        if not _HEX64.fullmatch(digest):
            raise ValueError("invalid_manifest_digest")
        normalized_digests[key] = digest
    path_rows = sorted(paths, key=str.lower)
    marker_rows = sorted(markers, key=lambda row: (row["marker_code"], row["parent_digest"]))
    return {
        "path_count": len(path_rows),
        "path_inventory_digest": _digest(path_rows),
        "manifest_digest_set_digest": _digest(normalized_digests),
        "manifest_digest_count": len(normalized_digests),
        "marker_rows": marker_rows,
        "marker_codes": sorted({row["marker_code"] for row in marker_rows}),
        "marker_parent_count": len(parents),
        "source_suffixes": sorted(suffixes),
        "raw_paths_stored": False,
        "raw_manifest_contents_stored": False,
    }


def _adapter_by_id(adapter_id: str) -> dict[str, Any] | None:
    target = str(adapter_id or "").lower()
    return next((dict(row) for row in _ADAPTERS if row["adapter_id"] == target), None)


def _detect(inventory: Mapping[str, Any], requested_adapter_id: str = "") -> dict[str, Any]:
    marker_codes = set(inventory.get("marker_codes") or [])
    candidates = [dict(row) for row in _ADAPTERS if marker_codes.intersection(row["marker_codes"])]
    delegated = sorted({value for marker, value in _EXISTING_DELEGATIONS.items() if marker in marker_codes})
    requested = str(requested_adapter_id or "").lower().strip()
    if requested:
        selected = _adapter_by_id(requested)
        if selected is None:
            return {"state": "adapter_blocked", "reason": "requested_adapter_unknown", "candidate_adapter_ids": sorted(row["adapter_id"] for row in candidates)}
        if not marker_codes.intersection(selected["marker_codes"]):
            return {"state": "adapter_blocked", "reason": "requested_adapter_marker_mismatch", "candidate_adapter_ids": sorted(row["adapter_id"] for row in candidates)}
        return {"state": "adapter_selected", "reason": "explicit_adapter_matches_verified_marker", "candidate_adapter_ids": sorted(row["adapter_id"] for row in candidates), "selected_adapter": selected}
    if len(candidates) == 1 and not delegated:
        return {"state": "adapter_selected", "reason": "single_verified_manifest_family", "candidate_adapter_ids": [candidates[0]["adapter_id"]], "selected_adapter": candidates[0]}
    if len(candidates) > 1:
        return {"state": "adapter_ambiguous", "reason": "multiple_broader_adapter_families_detected", "candidate_adapter_ids": sorted(row["adapter_id"] for row in candidates)}
    if candidates and delegated:
        return {"state": "adapter_ambiguous", "reason": "mixed_existing_and_broader_adapter_families", "candidate_adapter_ids": sorted([row["adapter_id"] for row in candidates] + delegated)}
    if delegated:
        return {"state": "adapter_delegated_existing", "reason": "existing_specialized_adapter_required", "candidate_adapter_ids": delegated, "delegated_adapter_ids": delegated}
    return {"state": "adapter_unsupported", "reason": "no_supported_manifest_family_detected", "candidate_adapter_ids": []}


def _upstream_basis(
    plan_id: str,
    expected_plan_digest: str,
    review_id: str,
    expected_review_digest: str,
    project_reference: str,
    runtime_root=None,
) -> dict[str, str]:
    if not any((plan_id, expected_plan_digest, review_id, expected_review_digest)):
        return {"orchestration_plan_id": "", "orchestration_plan_digest": "", "orchestration_review_id": "", "orchestration_review_digest": ""}
    plan = load_multi_tool_orchestration_plan(str(plan_id or "").lower(), runtime_root=runtime_root)
    review = load_multi_tool_orchestration_review(str(review_id or "").lower(), runtime_root=runtime_root)
    if not plan.get("ok") or not review.get("ok"):
        raise ValueError("upstream_orchestration_record_missing_or_tampered")
    if plan.get("plan_digest") != str(expected_plan_digest or "").lower():
        raise ValueError("stale_orchestration_plan_digest")
    if review.get("review_digest") != str(expected_review_digest or "").lower():
        raise ValueError("stale_orchestration_review_digest")
    if review.get("plan_id") != plan.get("plan_id") or review.get("plan_digest") != plan.get("plan_digest"):
        raise ValueError("orchestration_review_lineage_mismatch")
    if review.get("disposition") != "accept_plan":
        raise ValueError("accepted_orchestration_plan_review_required")
    if project_reference and plan.get("project_reference") != project_reference:
        raise ValueError("project_reference_mismatch")
    return {
        "orchestration_plan_id": plan["plan_id"],
        "orchestration_plan_digest": plan["plan_digest"],
        "orchestration_review_id": review["review_id"],
        "orchestration_review_digest": review["review_digest"],
    }


def _load_record(directory: str, record_id: str, digest_field: str, runtime_root=None) -> dict[str, Any]:
    path = _path(directory, record_id, runtime_root)
    if not path.is_file():
        return _failure("broader_project_adapter_record_missing", record_id)
    row = _read_json(path)
    if not isinstance(row, dict) or not _valid(row, digest_field):
        return _failure("broader_project_adapter_record_tampered", record_id)
    return {"ok": True, **row, **_base()}


def load_broader_project_adapter_assessment(assessment_id: str, *, runtime_root=None) -> dict[str, Any]:
    return _load_record("broader_project_adapter_assessments", assessment_id, "assessment_record_digest", runtime_root)


def load_broader_project_adapter_review(review_id: str, *, runtime_root=None) -> dict[str, Any]:
    return _load_record("broader_project_adapter_reviews", review_id, "review_record_digest", runtime_root)


def prepare_broader_project_adapter_assessment(
    project_reference: str,
    *,
    relative_paths: Iterable[Any],
    manifest_digests: Mapping[str, Any] | None = None,
    requested_adapter_id: str = "",
    orchestration_plan_id: str = "",
    expected_orchestration_plan_digest: str = "",
    orchestration_review_id: str = "",
    expected_orchestration_review_digest: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    try:
        project = str(project_reference or "").lower().strip()
        if not _PROJECT_REF.fullmatch(project):
            raise ValueError("invalid_project_reference")
        inventory = _normalize_inventory(relative_paths, manifest_digests)
        detection = _detect(inventory, requested_adapter_id)
        upstream = _upstream_basis(
            orchestration_plan_id, expected_orchestration_plan_digest,
            orchestration_review_id, expected_orchestration_review_digest,
            project, runtime_root,
        )
        registry = adapter_registry()
        basis = {
            "project_reference": project,
            "inventory": inventory,
            "requested_adapter_id": str(requested_adapter_id or "").lower().strip(),
            "detection_state": detection["state"],
            "detection_reason": detection["reason"],
            "candidate_adapter_ids": detection.get("candidate_adapter_ids") or [],
            "selected_adapter_id": (detection.get("selected_adapter") or {}).get("adapter_id", ""),
            "delegated_adapter_ids": detection.get("delegated_adapter_ids") or [],
            "registry_digest": registry["registry_digest"],
            **upstream,
        }
        assessment_digest = _digest(basis)
        assessment_id = f"adapter_assessment_{assessment_digest[:24]}"
        with _lock(runtime_root):
            existing_path = _path("broader_project_adapter_assessments", assessment_id, runtime_root)
            if existing_path.is_file():
                existing = load_broader_project_adapter_assessment(assessment_id, runtime_root=runtime_root)
                if existing.get("assessment_digest") != assessment_digest:
                    raise ValueError("assessment_id_collision")
                return existing
            selected = detection.get("selected_adapter") or {}
            row = {
                "assessment_id": assessment_id,
                "assessment_digest": assessment_digest,
                "status": "broader_project_adapter_ready_for_operator_review",
                **basis,
                "selected_adapter_contract_digest": selected.get("adapter_contract_digest", ""),
                "project_kind": selected.get("project_kind", ""),
                "language": selected.get("language", ""),
                "build_system": selected.get("build_system", ""),
                "runtime_dependencies": selected.get("runtime_dependencies", []),
                "generated_directories": selected.get("generated_directories", []),
                "build_command_template": selected.get("build_command_template", []),
                "test_command_template": selected.get("test_command_template", []),
                "test_evidence_kind": selected.get("test_evidence_kind", ""),
                "review_required_before_orchestration_blueprint": True,
                "fresh_separate_execution_authority_required": True,
                **_base(),
            }
            row = _sealed(row, "assessment_record_digest")
            _atomic_json(existing_path, row)
            return {"ok": True, **row, **_base()}
    except Exception as exc:
        return _failure("broader_project_adapter_assessment_blocked", str(exc))


def review_broader_project_adapter_assessment(
    assessment_id: str,
    *,
    expected_assessment_digest: str,
    disposition: str,
    exact_phrase: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    decision = str(disposition or "").lower()
    if decision not in REVIEW_DISPOSITIONS:
        return _failure("broader_project_adapter_review_invalid", "unsupported_disposition")
    try:
        with _lock(runtime_root):
            assessment = load_broader_project_adapter_assessment(str(assessment_id or "").lower(), runtime_root=runtime_root)
            if not assessment.get("ok"):
                raise ValueError("assessment_missing_or_tampered")
            if assessment.get("assessment_digest") != str(expected_assessment_digest or "").lower():
                raise ValueError("stale_assessment_digest")
            if decision == "accept_adapter" and assessment.get("detection_state") != "adapter_selected":
                raise ValueError("selected_adapter_required_for_acceptance")
            index_path = _path("broader_project_adapter_review_indexes", assessment["assessment_id"], runtime_root)
            if index_path.is_file():
                index = _read_json(index_path)
                existing = load_broader_project_adapter_review(index.get("review_id", ""), runtime_root=runtime_root)
                if existing.get("disposition") != decision:
                    raise ValueError("assessment_already_reviewed_with_different_disposition")
                return existing
            basis = {
                "assessment_id": assessment["assessment_id"],
                "assessment_digest": assessment["assessment_digest"],
                "project_reference": assessment["project_reference"],
                "selected_adapter_id": assessment.get("selected_adapter_id", ""),
                "disposition": decision,
            }
            review_digest = _digest(basis)
            review_id = f"adapter_review_{review_digest[:24]}"
            row = {
                "review_id": review_id,
                "review_digest": review_digest,
                "status": "broader_project_adapter_review_recorded",
                **basis,
                "exact_phrase_digest": _digest(str(exact_phrase or "")),
                "adapter_interpretation_accepted": decision == "accept_adapter",
                "execution_authority_created": False,
                "commands_authorized": False,
                "tests_authorized": False,
                "dependency_installation_authorized": False,
                **_base(),
            }
            row = _sealed(row, "review_record_digest")
            _atomic_json(_path("broader_project_adapter_reviews", review_id, runtime_root), row)
            _atomic_json(index_path, {"review_id": review_id, "review_digest": review_digest})
            return {"ok": True, **row, **_base()}
    except Exception as exc:
        return _failure("broader_project_adapter_review_blocked", str(exc))


def prepare_adapter_orchestration_blueprint(
    assessment_id: str,
    *,
    expected_assessment_digest: str,
    review_id: str,
    expected_review_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    try:
        assessment = load_broader_project_adapter_assessment(str(assessment_id or "").lower(), runtime_root=runtime_root)
        review = load_broader_project_adapter_review(str(review_id or "").lower(), runtime_root=runtime_root)
        if not assessment.get("ok") or not review.get("ok"):
            raise ValueError("assessment_or_review_missing_or_tampered")
        if assessment.get("assessment_digest") != str(expected_assessment_digest or "").lower():
            raise ValueError("stale_assessment_digest")
        if review.get("review_digest") != str(expected_review_digest or "").lower():
            raise ValueError("stale_review_digest")
        if review.get("assessment_id") != assessment.get("assessment_id") or review.get("assessment_digest") != assessment.get("assessment_digest"):
            raise ValueError("review_lineage_mismatch")
        if review.get("disposition") != "accept_adapter" or assessment.get("detection_state") != "adapter_selected":
            raise ValueError("accepted_selected_adapter_required")
        adapter_id = assessment["selected_adapter_id"]
        build_contract = _digest({"adapter_id": adapter_id, "kind": "bounded_build", "command": assessment.get("build_command_template")})
        test_contract = _digest({"adapter_id": adapter_id, "kind": "bounded_test", "command": assessment.get("test_command_template")})
        tools = [
            {"tool_id": "tool_project_adapter_inspector", "capability_codes": ["inspect_project_adapter"], "consumes": ["project_reference"], "produces": ["adapter_evidence"], "input_contract_digest": assessment["assessment_digest"], "output_contract_digest": assessment["selected_adapter_contract_digest"], "risk_level": "low", "provider_required": False, "language_runtime_required": False, "mutation_capable": False},
            {"tool_id": "tool_language_build_adapter", "capability_codes": ["prepare_language_build"], "consumes": ["adapter_evidence"], "produces": ["build_evidence"], "input_contract_digest": assessment["selected_adapter_contract_digest"], "output_contract_digest": build_contract, "risk_level": "medium", "provider_required": False, "language_runtime_required": True, "mutation_capable": False},
            {"tool_id": "tool_language_test_adapter", "capability_codes": ["prepare_language_tests"], "consumes": ["build_evidence"], "produces": ["test_evidence"], "input_contract_digest": build_contract, "output_contract_digest": test_contract, "risk_level": "medium", "provider_required": False, "language_runtime_required": True, "mutation_capable": False},
        ]
        steps = [
            {"step_id": "step_adapter_inspect", "ordinal": 1, "tool_id": "tool_project_adapter_inspector", "action_code": "inspect_project_adapter", "depends_on": [], "consumes": ["project_reference"], "produces": ["adapter_evidence"], "input_contract_digest": assessment["assessment_digest"], "output_contract_digest": assessment["selected_adapter_contract_digest"]},
            {"step_id": "step_adapter_build", "ordinal": 2, "tool_id": "tool_language_build_adapter", "action_code": "prepare_language_build", "depends_on": ["step_adapter_inspect"], "consumes": ["adapter_evidence"], "produces": ["build_evidence"], "input_contract_digest": assessment["selected_adapter_contract_digest"], "output_contract_digest": build_contract},
            {"step_id": "step_adapter_test", "ordinal": 3, "tool_id": "tool_language_test_adapter", "action_code": "prepare_language_tests", "depends_on": ["step_adapter_build"], "consumes": ["build_evidence"], "produces": ["test_evidence"], "input_contract_digest": build_contract, "output_contract_digest": test_contract},
        ]
        row = {
            "ok": True,
            "status": "broader_project_adapter_orchestration_blueprint_ready",
            "assessment_id": assessment["assessment_id"],
            "assessment_digest": assessment["assessment_digest"],
            "review_id": review["review_id"],
            "review_digest": review["review_digest"],
            "project_reference": assessment["project_reference"],
            "selected_adapter_id": adapter_id,
            "project_kind": assessment.get("project_kind"),
            "initial_artifact_types": ["project_reference"],
            "tools": tools,
            "steps": steps,
            "fresh_separate_v1237_plan_review_required": True,
            "blueprint_does_not_invoke_tools": True,
            "blueprint_does_not_authorize_commands_or_tests": True,
            **_base(),
        }
        row["blueprint_digest"] = _digest(row)
        return row
    except Exception as exc:
        return _failure("broader_project_adapter_blueprint_blocked", str(exc))


_ASSESSMENT_PUBLIC = (
    "assessment_id", "assessment_digest", "status", "project_reference", "detection_state", "detection_reason",
    "candidate_adapter_ids", "selected_adapter_id", "delegated_adapter_ids", "project_kind", "language", "build_system",
    "runtime_dependencies", "generated_directories", "test_evidence_kind", "registry_digest", "orchestration_plan_id",
    "orchestration_plan_digest", "orchestration_review_id", "orchestration_review_digest", "content_free",
)
_REVIEW_PUBLIC = (
    "review_id", "review_digest", "status", "assessment_id", "assessment_digest", "project_reference",
    "selected_adapter_id", "disposition", "adapter_interpretation_accepted", "execution_authority_created", "content_free",
)


def _public_list(directory: str, digest_field: str, fields: Iterable[str], plural: str, runtime_root=None) -> dict[str, Any]:
    root = _dir(directory, runtime_root)
    rows: list[dict[str, Any]] = []
    if root.is_dir():
        for path in sorted(root.glob("*.json"))[:MAX_RECORDS]:
            raw = _read_json(path)
            if isinstance(raw, dict) and _valid(raw, digest_field):
                rows.append({field: raw.get(field) for field in fields})
    result = {"ok": True, "status": f"broader_project_adapter_{plural}_ready", f"{plural[:-1]}_count": len(rows), plural: rows, **_base()}
    result[f"{plural}_digest"] = _digest(rows)
    return result


def public_broader_project_adapter_assessments(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("broader_project_adapter_assessments", "assessment_record_digest", _ASSESSMENT_PUBLIC, "assessments", runtime_root)


def public_broader_project_adapter_reviews(*, runtime_root=None) -> dict[str, Any]:
    return _public_list("broader_project_adapter_reviews", "review_record_digest", _REVIEW_PUBLIC, "reviews", runtime_root)


def inspect_broader_project_adapter_assessment(assessment_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = load_broader_project_adapter_assessment(str(assessment_id or "").lower(), runtime_root=runtime_root)
    if not row.get("ok"):
        return row
    return {"ok": True, "status": "broader_project_adapter_assessment_ready", "assessment": {field: row.get(field) for field in _ASSESSMENT_PUBLIC}, **_base()}


def broader_project_adapter_response(row: Mapping[str, Any]) -> str:
    status = str(row.get("status") or "")
    if status == "broader_project_adapter_review_recorded":
        return f"Broader project adapter review {row.get('review_id')} recorded as {row.get('disposition')}. No command, test, installation, provider call, project change, launch, or resume was authorized."
    if status.endswith("_ready"):
        return "The content-free broader project adapter inspection is ready. No file contents were read and no command, test, dependency installation, or project change occurred."
    return f"The broader project adapter control was blocked: {row.get('reason') or status or 'unknown reason'}."


def process_broader_project_language_adapter_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    match = _REVIEW.fullmatch(text)
    if match:
        row = review_broader_project_adapter_assessment(
            match.group("assessment"), expected_assessment_digest=match.group("digest"),
            disposition=match.group("decision"), exact_phrase=text, runtime_root=runtime_root,
        )
        return {"active": True, "response": broader_project_adapter_response(row), "broader_project_language_adapter": row}
    if _SHOW_ASSESSMENTS.fullmatch(text):
        row = public_broader_project_adapter_assessments(runtime_root=runtime_root)
        return {"active": True, "response": broader_project_adapter_response(row), "broader_project_language_adapter": row}
    if _SHOW_REVIEWS.fullmatch(text):
        row = public_broader_project_adapter_reviews(runtime_root=runtime_root)
        return {"active": True, "response": broader_project_adapter_response(row), "broader_project_language_adapter": row}
    if _SHOW_REGISTRY.fullmatch(text):
        row = adapter_registry()
        return {"active": True, "response": broader_project_adapter_response(row), "broader_project_language_adapter": row}
    match = _SHOW_ASSESSMENT.fullmatch(text)
    if match:
        row = inspect_broader_project_adapter_assessment(match.group("assessment"), runtime_root=runtime_root)
        return {"active": True, "response": broader_project_adapter_response(row), "broader_project_language_adapter": row}
    return {"active": False}


def build_broader_project_language_adapter_contract() -> dict[str, Any]:
    row = {
        "ok": True,
        "status": "broader_project_language_adapter_contract_ready",
        "roadmap_path": "Balanced Mind-and-Action Path 3",
        "adapter_count": len(_ADAPTERS),
        "adapter_ids": sorted(row["adapter_id"] for row in _ADAPTERS),
        "manifest_and_layout_detection_only": True,
        "java_maven_and_gradle_supported": True,
        "dotnet_rust_go_php_supported": True,
        "existing_javascript_web_python_delegated": True,
        "ambiguous_mixed_and_nested_projects_fail_closed": True,
        "content_free_inventory_digests": True,
        "manifest_contents_not_read": True,
        "bounded_build_and_test_command_templates": True,
        "v1237_compatible_orchestration_blueprint": True,
        "fresh_v1237_plan_review_required_for_use": True,
        "ordinary_chat_exact_review_controls": True,
        "get_only_api_inspection": True,
        "restart_replay_stale_tamper_privacy_contradiction_hardening_required": True,
        "adapter_acceptance_does_not_authorize_execution": True,
        "blueprint_does_not_authorize_next_tool": True,
        "unsupported_layouts_defer_without_guessing": True,
        **_base(),
    }
    row["contract_digest"] = _digest(row)
    return row
