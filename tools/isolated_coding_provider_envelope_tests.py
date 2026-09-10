from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "conscious_agent"))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import local_model
from python_test_adapter import _is_test_path as _adapter_is_test_path
from isolated_coding_execution import (
    CODING_CONTEXT_SIZE,
    CODING_MAX_TOKENS,
    CODING_READ_TIMEOUT_SECONDS,
    MAX_PROVIDER_CONTEXT_BYTES,
    _bounded_verification_files,
    _configured_coding_generate,
    _generation_repair_guidance,
    _is_project_test_path,
    _load_or_generate_attempt,
    _provider_prompt,
    _read_provider_context,
    _safe_generation_rejection_code,
    _validate_generation,
)

CHECKS: list[str] = []


def require(value: object, label: str) -> None:
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


configured = local_model.LocalModelConfig(
    provider="ollama",
    model="fixture-model",
    context_size=8192,
    read_timeout_seconds=120.0,
    generation=local_model.GenerationSettings(max_tokens=350, temperature=0.45),
)
captured: dict[str, object] = {}
real_config_class = local_model.LocalModelConfig
real_client_class = local_model.LocalModelClient


class FixtureConfig:
    @classmethod
    def from_settings(cls):
        return configured


class FixtureClient:
    def __init__(self, config):
        captured["config"] = config

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def generate(self, prompt):
        captured["prompt"] = prompt
        return "fixture-response"


try:
    local_model.LocalModelConfig = FixtureConfig
    local_model.LocalModelClient = FixtureClient
    require(_configured_coding_generate("bounded prompt") == "fixture-response", "coding_provider_response_returned")
finally:
    local_model.LocalModelConfig = real_config_class
    local_model.LocalModelClient = real_client_class

coding_config = captured["config"]
require(coding_config.provider == configured.provider and coding_config.model == configured.model, "configured_provider_and_model_preserved")
require(coding_config.context_size >= CODING_CONTEXT_SIZE, "coding_context_budget_applied")
require(coding_config.generation.max_tokens >= CODING_MAX_TOKENS, "coding_output_budget_applied")
require(coding_config.read_timeout_seconds >= CODING_READ_TIMEOUT_SECONDS, "coding_timeout_budget_applied")
require(coding_config.generation.temperature <= 0.2, "coding_generation_is_deterministic")
require(coding_config.structured_json is True, "coding_provider_native_json_mode_enabled")
require(configured.context_size == 8192 and configured.generation.max_tokens == 350 and configured.structured_json is False, "ordinary_model_configuration_unchanged")
require(_safe_generation_rejection_code(ValueError("syntax_invalid:conscious_agent/example.py")) == "syntax_invalid", "safe_rejection_prefix_is_preserved")
require("occurs once" in _generation_repair_guidance("compact_replacement_not_unique"), "duplicate_replacement_gets_bounded_repair_guidance")
require("parses" in _generation_repair_guidance("syntax_invalid"), "syntax_rejection_gets_bounded_repair_guidance")

with tempfile.TemporaryDirectory(prefix="eid-coding-provider-failure-") as directory:
    root = Path(directory) / "workspace"
    runtime = Path(directory) / "runtime"
    root.mkdir()
    (root / "main.py").write_text("VALUE = 1\n", encoding="utf-8")

    def fail_provider(_prompt: str) -> str:
        raise local_model.LocalModelTimeoutError("private provider detail")

    failed = _load_or_generate_attempt(
        request={"request_id": "devc_" + "a" * 24, "user_objective": "Fixture"},
        plan={"context_paths": ["main.py"]},
        inspection={},
        root=root,
        execution_digest="b" * 64,
        attempt_number=1,
        previous_outcome=None,
        runtime_root=runtime,
        provider_generate=fail_provider,
    )
    require(failed["status"] == "isolated_coding_provider_failed", "provider_failure_classified")
    require(failed["provider_contacted"] is True, "provider_contact_truth_preserved")
    require(failed["provider_failure_class"] == "LocalModelTimeoutError", "redacted_failure_class_preserved")
    require("private provider detail" not in json.dumps(failed), "provider_error_content_redacted")

with tempfile.TemporaryDirectory(prefix="eid-coding-context-rejection-") as directory:
    root = Path(directory) / "workspace"
    runtime = Path(directory) / "runtime"
    root.mkdir()
    rejected_context = _load_or_generate_attempt(
        request={"request_id": "devc_" + "9" * 24, "user_objective": "Fixture"},
        plan={"context_paths": ["missing.py"]},
        inspection={},
        root=root,
        execution_digest="8" * 64,
        attempt_number=1,
        previous_outcome=None,
        runtime_root=runtime,
        provider_generate=lambda _prompt: "must not run",
    )
    require(rejected_context["status"] == "isolated_coding_provider_context_rejected", "context_rejection_classified")
    require(rejected_context["provider_context_rejection_code"] == "provider_context_empty", "context_rejection_code_preserved")
    require(rejected_context["provider_contacted"] is False, "context_rejection_preserves_no_provider_contact")

with tempfile.TemporaryDirectory(prefix="eid-coding-generation-rejection-") as directory:
    root = Path(directory) / "workspace"
    runtime = Path(directory) / "runtime"
    root.mkdir()
    (root / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
    rejected = _load_or_generate_attempt(
        request={"request_id": "devc_" + "b" * 24, "user_objective": "Fixture"},
        plan={"context_paths": ["main.py"]},
        inspection={},
        root=root,
        execution_digest="c" * 64,
        attempt_number=1,
        previous_outcome=None,
        runtime_root=runtime,
        provider_generate=lambda _prompt: "provider-controlled malformed output with private text",
    )
    require(rejected["status"] == "isolated_coding_generation_rejected", "generation_rejection_classified")
    require(rejected["provider_contacted"] is True, "generation_rejection_preserves_provider_contact_truth")
    require(bool(re.fullmatch(r"[a-z0-9_]{1,80}", rejected["generation_rejection_code"])), "generation_rejection_code_is_content_free")
    require("provider-controlled" not in json.dumps(rejected), "rejected_provider_output_not_persisted")

with tempfile.TemporaryDirectory(prefix="eid-compact-coding-response-") as directory:
    root = Path(directory)
    (root / "main.py").write_text("def answer():\n    return 'old'\n", encoding="utf-8")
    compact = json.dumps({
        "authority": {
            "request_id": "devc_" + "c" * 24,
            "execution_digest": "d" * 64,
            "attempt": 1,
        },
        "edits": [{
            "path": "main.py",
            "replacements": [{"old": "return 'old'", "new": "return 'new'"}],
        }],
        "creates": [{
            "path": "tools/product_repair_fixture_tests.py",
            "content": "assert True\n",
        }],
    })
    changes = _validate_generation(
        compact,
        request_id="devc_" + "c" * 24,
        execution_digest="d" * 64,
        attempt_number=1,
        root=root,
    )
    require(len(changes) == 2, "compact_edit_and_create_validated")
    require("return 'new'" in changes[0]["content"] and "return 'old'" not in changes[0]["content"], "compact_exact_replacement_materialized")
    require(changes[1]["operation"] == "create", "compact_new_test_creation_preserved")
    require((root / "main.py").read_text(encoding="utf-8").endswith("return 'old'\n"), "compact_validation_does_not_modify_workspace")

    (root / "focused_tests.py").write_text(
        "FIXTURE = 'My tomato garden needs spacing advice'\n",
        encoding="utf-8",
    )
    overfit = {
        "edits": [{
            "path": "main.py",
            "replacements": [{
                "old": "return 'old'",
                "new": "return 'My tomato garden needs spacing advice'",
            }],
        }],
        "creates": [],
    }
    try:
        _validate_generation(
            json.dumps(overfit),
            request_id="devc_" + "c" * 24,
            execution_digest="d" * 64,
            attempt_number=1,
            root=root,
            test_paths=["focused_tests.py"],
        )
    except ValueError as exc:
        require(str(exc) == "test_fixture_literal_leakage", "test_fixture_literal_overfit_is_rejected")
    else:
        raise AssertionError("test_fixture_literal_overfit_is_rejected")

    server_bound = json.loads(compact)
    server_bound.pop("authority")
    server_bound_changes = _validate_generation(
        json.dumps(server_bound),
        request_id="devc_" + "c" * 24,
        execution_digest="d" * 64,
        attempt_number=1,
        root=root,
    )
    require(len(server_bound_changes) == 2, "provider_may_omit_server_owned_authority")

    mismatched = json.loads(compact)
    mismatched["authority"]["request_id"] = "devc_" + "0" * 24
    try:
        _validate_generation(
            json.dumps(mismatched),
            request_id="devc_" + "c" * 24,
            execution_digest="d" * 64,
            attempt_number=1,
            root=root,
        )
    except ValueError as exc:
        require(str(exc) == "execution_authority_binding_rejected", "volunteered_mismatched_authority_rejected")
    else:
        raise AssertionError("volunteered_mismatched_authority_rejected")

    legacy = json.dumps({
        "authority": {
            "request_id": "devc_" + "c" * 24,
            "execution_digest": "d" * 64,
            "attempt": 1,
        },
        "files": [{
            "path": "main.py",
            "operation": "modify",
            "content": "def answer():\n    return 'legacy'\n",
        }],
    })
    legacy_changes = _validate_generation(
        legacy,
        request_id="devc_" + "c" * 24,
        execution_digest="d" * 64,
        attempt_number=1,
        root=root,
    )
    require(legacy_changes[0]["content"].endswith("return 'legacy'\n"), "legacy_full_file_contract_remains_supported")

    duplicate = compact.replace("return 'old'", "")
    try:
        _validate_generation(
            duplicate,
            request_id="devc_" + "c" * 24,
            execution_digest="d" * 64,
            attempt_number=1,
            root=root,
        )
    except ValueError as exc:
        require(str(exc) == "compact_replacement_content_invalid", "empty_compact_match_rejected")
    else:
        raise AssertionError("empty_compact_match_rejected")

with tempfile.TemporaryDirectory(prefix="eid-bounded-coding-context-") as directory:
    root = Path(directory)
    for index in range(3):
        (root / f"module_{index}.py").write_text(f"VALUE_{index} = '" + ("x" * 14_000) + "'\n", encoding="utf-8")
    prompt = _provider_prompt(
        request={"request_id": "devc_" + "e" * 24, "user_objective": "Fixture"},
        plan={"context_paths": [f"module_{index}.py" for index in range(3)]},
        inspection={},
        root=root,
        execution_digest="f" * 64,
        attempt_number=1,
        previous_outcome=None,
    )
    workspace_files = json.loads(prompt)["workspace_files"]
    task_text = json.loads(prompt)["task"]
    require(len(workspace_files) == 2, "provider_context_stops_at_coding_byte_budget")
    require(sum(len(row["content"].encode("utf-8")) for row in workspace_files) <= MAX_PROVIDER_CONTEXT_BYTES, "provider_context_respects_coding_byte_budget")
    require("focused tests are verification evidence" in task_text, "coding_prompt_treats_tests_as_evidence")
    require("Do not copy or special-case prose literals" in task_text, "coding_prompt_forbids_fixture_literal_overfit")

with tempfile.TemporaryDirectory(prefix="eid-relevant-coding-excerpt-") as directory:
    root = Path(directory)
    oversized = "".join(f"def unrelated_{index}():\n    return {index}\n" for index in range(2200))
    target = "def assemble_context(casual_fast_path):\n    if casual_fast_path:\n        return 'ACTIVE THREAD TURN'\n"
    oversized += target
    (root / "conversation_context.py").write_text(oversized, encoding="utf-8")
    (root / "focused_tests.py").write_text(
        "def test_active_thread():\n    assert 'ACTIVE THREAD TURN'\n",
        encoding="utf-8",
    )
    excerpt_rows = _read_provider_context(
        root,
        ["conversation_context.py", "focused_tests.py"],
        relevance_text="repair active thread conversation target",
    )
    require(excerpt_rows[0].get("excerpt") is True, "oversized_first_context_file_uses_bounded_excerpt")
    require("ACTIVE THREAD TURN" in excerpt_rows[0]["content"], "bounded_excerpt_selects_attributable_target")
    require(target in excerpt_rows[0]["content"], "bounded_excerpt_preserves_exact_replacement_source")
    require(any(row["path"] == "focused_tests.py" for row in excerpt_rows), "focused_test_context_survives_large_source_file")
    require(sum(len(row["content"].encode("utf-8")) for row in excerpt_rows) <= MAX_PROVIDER_CONTEXT_BYTES, "relevant_excerpt_bundle_respects_byte_budget")

verification_rows = [
    {"relative_path": "conscious_agent/target.py", "relative_path_digest": "target"},
    {"relative_path": "tools/test_focused.py", "relative_path_digest": "focused"},
    {"relative_path": "tools/unrelated_tests.py", "relative_path_digest": "unrelated"},
]
verification_scope = _bounded_verification_files(
    verification_rows,
    {"verification_plan": ["tools/test_focused.py", "Compile changed Python modules"]},
    {"changes": [{"relative_path": "conscious_agent/target.py"}]},
)
require([row["relative_path"] for row in verification_scope] == ["conscious_agent/target.py", "tools/test_focused.py"], "verification_scope_uses_changed_and_bound_test_files")
generic_scope = _bounded_verification_files(
    [
        {"relative_path": "main.py", "relative_path_digest": "main"},
        {"relative_path": "test_main.py", "relative_path_digest": "test"},
    ],
    {"verification_plan": ["Compile Python", "Run project tests"]},
    {"changes": [{"relative_path": "main.py"}]},
)
require([row["relative_path"] for row in generic_scope] == ["main.py", "test_main.py"], "generic_test_requirement_discovers_bounded_project_tests")
require(_is_project_test_path("tools/v1500_9_integrated_daily_use_conversation_tests.py"), "eidolon_versioned_test_naming_is_recognized")
require(_adapter_is_test_path("tools/v1500_9_integrated_daily_use_conversation_tests.py"), "python_adapter_recognizes_eidolon_versioned_test_naming")

print(json.dumps({
    "ok": True,
    "suite": "isolated-coding-provider-envelope",
    "passed": len(CHECKS),
    "total": len(CHECKS),
    "checks": CHECKS,
}, sort_keys=True))
