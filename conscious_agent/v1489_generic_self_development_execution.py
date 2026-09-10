from __future__ import annotations

"""Provider-backed implementation of a bounded v1489 self-development proposal.

The configured local model may author structured edits only inside the already
prepared disposable workspace.  This module deliberately grants no authority
to install the candidate or mutate the active source tree.
"""

import ast
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Mapping

from isolated_self_modification import _apply_transactionally
from isolated_self_modification_foundations import (
    _safe_relative,
    source_only_manifest,
    source_only_manifest_from_content_digests,
)
from json_storage import write_json_atomic
from symbol_level_refactoring import (
    build_symbol_extraction_changes,
    build_symbol_selection_prompt,
    parse_symbol_selection,
)


MAX_ATTEMPTS = 2
MAX_ALLOWED_FILES = 6
MAX_EDITS_PER_FILE = 16
MAX_CONTEXT_CHARS = 12_000
MAX_OUTPUT_CHARS = 512_000
MAX_CHANGED_BYTES = 2 * 1024 * 1024
DENIED_PARTS = {"data", "runtime", ".git", "__pycache__", "secrets", "private"}


class GenericSelfDevelopmentError(RuntimeError):
    def __init__(
        self,
        code: str,
        *,
        provider_request_count: int = 0,
        failure_codes: list[str] | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.provider_request_count = provider_request_count
        self.failure_codes = list(failure_codes or [])


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _allowed_paths(proposal: Mapping[str, Any]) -> list[str]:
    rows: list[str] = []
    for value in proposal.get("affected_scope") or []:
        text = str(value or "").strip().replace("\\", "/")
        if not text.endswith((".py", ".js", ".json", ".html", ".css", ".md")):
            continue
        try:
            rel = _safe_relative(text)
        except ValueError as exc:
            raise GenericSelfDevelopmentError("generic_self_development_private_path_rejected") from exc
        if any(part.casefold() in DENIED_PARTS for part in PurePosixPath(rel).parts):
            raise GenericSelfDevelopmentError("generic_self_development_private_path_rejected")
        if rel.casefold() not in {row.casefold() for row in rows}:
            rows.append(rel)
    if not rows or len(rows) > MAX_ALLOWED_FILES:
        raise GenericSelfDevelopmentError("generic_self_development_scope_invalid")
    return rows


def _objective_tokens(proposal: Mapping[str, Any]) -> set[str]:
    text = " ".join(
        str(proposal.get(key) or "")
        for key in ("improvement_class", "proposed_change", "expected_benefit")
    ).casefold()
    ignored = {
        "and", "behind", "bounded", "existing", "extract", "extraction", "helpers",
        "into", "module", "preserve", "retained", "the", "with", "without",
    }
    return {token for token in re.findall(r"[a-z][a-z0-9_]{3,}", text) if token not in ignored}


def _source_excerpt(path: Path, proposal: Mapping[str, Any], *, max_chars: int) -> str:
    if not path.exists():
        return "<new file>"
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) <= max_chars:
        return text
    if path.suffix.casefold() != ".py":
        return text[:max_chars]
    lines = text.splitlines()
    tokens = _objective_tokens(proposal)
    sections: list[tuple[int, int, int, str]] = []
    try:
        tree = ast.parse(text)
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            name = str(getattr(node, "name", "")).casefold()
            block = "\n".join(lines[node.lineno - 1 : getattr(node, "end_lineno", node.lineno)])
            haystack = (name + " " + block[:1500]).casefold()
            score = sum(4 if token in name else 1 for token in tokens if token in haystack)
            if score:
                sections.append((score, node.lineno, getattr(node, "end_lineno", node.lineno), block))
    except SyntaxError:
        sections = []
    sections.sort(key=lambda row: (-row[0], row[1]))
    header = "\n".join(lines[:80])
    selected = [f"# SOURCE LINES 1-80\n{header}"[:max_chars]]
    used = len(selected[0])
    for _, start, end, block in sections:
        rendered = f"\n# SOURCE LINES {start}-{end}\n{block}"
        if used + len(rendered) > max_chars:
            continue
        selected.append(rendered)
        used += len(rendered)
        if used >= max_chars - 2_000:
            break
    return "\n".join(selected)


def _prompt(
    workspace: Path,
    proposal: Mapping[str, Any],
    allowed: list[str],
    *,
    attempt: int,
    prior_failure: str = "",
) -> str:
    existing_count = max(1, sum(1 for rel in allowed if (workspace / rel).is_file()))
    per_file_budget = max(2_000, MAX_CONTEXT_CHARS // existing_count)
    sources = [
        {
            "path": rel,
            "exists": (workspace / rel).is_file(),
            "content_or_excerpt": _source_excerpt(
                workspace / rel, proposal, max_chars=per_file_budget
            ),
        }
        for rel in allowed
    ]
    request = {
        "task": "Implement the approved bounded change. Return exactly one JSON object and no markdown.",
        "objective": {
            "class": proposal.get("improvement_class"),
            "change": proposal.get("proposed_change"),
            "benefit": proposal.get("expected_benefit"),
        },
        "authority": {
            "proposal_id": proposal.get("proposal_id"),
            "proposal_digest": proposal.get("proposal_digest"),
            "attempt": attempt,
            "active_source_mutation_authorized": False,
            "workspace_only": True,
        },
        "schema": {
            "authority": {"proposal_id": "exact", "proposal_digest": "exact"},
            "changes": [
                {
                    "path": "one exact allowed path",
                    "action": "create or modify",
                    "content": "full content for create",
                    "edits": [{"find": "exact unique existing text", "replace": "replacement text"}],
                }
            ],
        },
        "constraints": {
            "allowed_paths": allowed,
            "modify_uses_edits": True,
            "create_uses_content": True,
            "preserve_public_behavior": True,
            "no_commands": True,
            "no_runtime_or_private_data": True,
            "max_edits_per_file": MAX_EDITS_PER_FILE,
        },
        "prior_failure": prior_failure[:1200],
        "sources": sources,
    }
    return json.dumps(request, sort_keys=True, separators=(",", ":"))


def _default_provider(prompt: str) -> str:
    from local_model import LocalModelClient, LocalModelConfig

    config = LocalModelConfig.from_settings()
    staged_generation = (
        "Create the new bounded helper module" in prompt
        or "Use the newly created helper module" in prompt
    )
    timeout = 300.0 if staged_generation else 240.0
    config = replace(config, read_timeout_seconds=max(timeout, config.read_timeout_seconds))
    requested_tokens = 4_096 if staged_generation else 2_048
    max_tokens = max(1_536, min(requested_tokens, config.context_size // 2))
    with LocalModelClient(config.with_generation(temperature=0.15, max_tokens=max_tokens)) as client:
        return client.generate(prompt)


def _record_private_provider_output(
    workspace: Path,
    proposal: Mapping[str, Any],
    *,
    stage: str,
    request_number: int,
    prompt: str,
    raw: str,
) -> None:
    proposal_workspace = workspace.parent
    workspaces_root = proposal_workspace.parent
    if workspaces_root.name != "workspaces" or proposal_workspace.name != str(proposal.get("proposal_id") or ""):
        return
    private_root = workspaces_root.parent / "provider_private" / proposal_workspace.name
    private_root.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": "1",
        "proposal_id": proposal.get("proposal_id"),
        "proposal_digest": proposal.get("proposal_digest"),
        "stage": stage,
        "request_number": request_number,
        "prompt_digest": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "raw_output_digest": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "raw_output": raw,
        "private_runtime_record": True,
        "source_only_packaged": False,
    }
    write_json_atomic(
        private_root / f"request-{request_number:02d}-{stage}.json",
        record,
        expected_type=dict,
        sort_keys=True,
        coordinate=False,
    )


def _parse_response(raw: str) -> Mapping[str, Any]:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("provider_output_empty")
    if len(raw) > MAX_OUTPUT_CHARS:
        raise ValueError("provider_output_too_large")
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        candidates: list[Mapping[str, Any]] = []
        for match in re.finditer(r"\{", text):
            try:
                candidate, _ = decoder.raw_decode(text[match.start() :])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, Mapping) and "authority" in candidate and "changes" in candidate:
                candidates.append(candidate)
        if not candidates:
            literal_segments = re.findall(r"```(?:json|python)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
            first_brace = text.find("{")
            last_brace = text.rfind("}")
            if first_brace >= 0 and last_brace > first_brace:
                literal_segments.append(text[first_brace : last_brace + 1])
            literal_candidates: list[Mapping[str, Any]] = []
            for segment in literal_segments:
                try:
                    candidate = ast.literal_eval(segment.strip())
                except (MemoryError, RecursionError, SyntaxError, ValueError):
                    continue
                if isinstance(candidate, Mapping) and "authority" in candidate and "changes" in candidate:
                    literal_candidates.append(candidate)
            unique = {_digest(candidate): candidate for candidate in literal_candidates}
            candidates.extend(unique.values())
        if len(candidates) != 1:
            raise ValueError("provider_output_not_single_structured_object")
        value = candidates[0]
    if not isinstance(value, Mapping):
        raise ValueError("provider_output_not_object")
    return value


def _created_file_prompt(
    workspace: Path,
    proposal: Mapping[str, Any],
    *,
    new_path: str,
    context_paths: list[str],
) -> str:
    existing_count = max(1, len(context_paths))
    sources = [
        {
            "path": rel,
            "content_or_excerpt": _source_excerpt(
                workspace / rel,
                proposal,
                max_chars=max(2_000, MAX_CONTEXT_CHARS // existing_count),
            ),
        }
        for rel in context_paths
    ]
    return json.dumps(
        {
            "task": "Create the new bounded helper module. Return only its complete source in one code fence.",
            "objective": proposal.get("proposed_change"),
            "benefit": proposal.get("expected_benefit"),
            "authority": {
                "proposal_id": proposal.get("proposal_id"),
                "proposal_digest": proposal.get("proposal_digest"),
                "workspace_only": True,
                "active_source_mutation_authorized": False,
            },
            "new_path": new_path,
            "constraints": {
                "preserve_behavior": True,
                "no_commands": True,
                "no_runtime_data": True,
                "complete_file_content": True,
            },
            "sources": sources,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _parse_created_file(raw: str, path: str) -> str:
    if not isinstance(raw, str) or not raw.strip() or len(raw) > MAX_OUTPUT_CHARS:
        raise ValueError("provider_created_file_output_invalid")
    fences = re.findall(r"```(?:python|py)?\s*(.*?)```", raw.strip(), flags=re.IGNORECASE | re.DOTALL)
    if len(fences) > 1:
        raise ValueError("provider_created_file_multiple_blocks")
    content = fences[0].strip() + "\n" if fences else raw.strip() + "\n"
    if len(content.encode("utf-8")) > MAX_CHANGED_BYTES:
        raise ValueError("provider_created_file_too_large")
    if path.endswith(".py"):
        tree = ast.parse(content, filename=path)
        meaningful = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Assign, ast.AnnAssign, ast.Import, ast.ImportFrom)
        if not any(isinstance(node, meaningful) for node in tree.body):
            raise ValueError("provider_created_python_module_has_no_definitions")
    return content


def _normalize_provider_edits(
    workspace: Path,
    proposal: Mapping[str, Any],
    allowed: list[str],
    response: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    authority = response.get("authority") or {}
    if authority.get("proposal_id") != proposal.get("proposal_id") or authority.get("proposal_digest") != proposal.get("proposal_digest"):
        raise ValueError("provider_authority_binding_rejected")
    rows = response.get("changes")
    if not isinstance(rows, list) or not rows or len(rows) > len(allowed):
        raise ValueError("provider_change_count_invalid")
    allowed_folded = {value.casefold(): value for value in allowed}
    seen: set[str] = set()
    transactional: list[dict[str, Any]] = []
    changed: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("provider_change_invalid")
        rel = _safe_relative(str(row.get("path") or ""))
        key = rel.casefold()
        if key not in allowed_folded or key in seen:
            raise ValueError("provider_path_outside_allowlist_or_duplicate")
        seen.add(key)
        rel = allowed_folded[key]
        target = workspace / rel
        action = str(row.get("action") or "")
        if action == "create":
            if target.exists() or not isinstance(row.get("content"), str):
                raise ValueError("provider_create_contract_invalid")
            content = str(row["content"])
        elif action == "modify":
            if not target.is_file():
                raise ValueError("provider_modify_target_missing")
            content = target.read_text(encoding="utf-8")
            edits = row.get("edits")
            if not isinstance(edits, list) or not edits or len(edits) > MAX_EDITS_PER_FILE:
                raise ValueError("provider_edit_count_invalid")
            for edit in edits:
                if not isinstance(edit, Mapping):
                    raise ValueError("provider_edit_invalid")
                find = edit.get("find")
                replace = edit.get("replace")
                if not isinstance(find, str) or not find or not isinstance(replace, str):
                    raise ValueError("provider_edit_contract_invalid")
                if content.count(find) != 1:
                    raise ValueError("provider_edit_anchor_not_unique")
                content = content.replace(find, replace, 1)
        else:
            raise ValueError("provider_action_rejected")
        if len(content.encode("utf-8")) > MAX_CHANGED_BYTES:
            raise ValueError("provider_changed_file_too_large")
        transactional.append({"relative_path": rel, "action": action, "content": content})
        changed.append(rel)
    return transactional, changed


def _selected_commands(workspace: Path, changed: list[str]) -> list[list[str]]:
    python_files = [rel for rel in changed if rel.endswith(".py")]
    commands: list[list[str]] = []
    if python_files:
        commands.append([sys.executable, "-m", "py_compile", *python_files])
    commands.append([sys.executable, "tools/v1489_product_capability_integration_tests.py"])
    commands.append([sys.executable, "tools/v1489_generic_self_development_execution_tests.py"])
    commands.append([sys.executable, "tools/v1489_symbol_level_refactoring_tests.py"])
    return commands


def _run_checks(workspace: Path, proposal_id: str, changed: list[str]) -> tuple[list[dict[str, Any]], str]:
    cache = workspace.parent / "verification_cache" / proposal_id
    cache.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPYCACHEPREFIX": str(cache)})
    receipts: list[dict[str, Any]] = []
    failure = ""
    for index, command in enumerate(_selected_commands(workspace, changed), start=1):
        started = time.monotonic()
        completed = subprocess.run(
            command, cwd=workspace, env=env, capture_output=True, text=True,
            timeout=180, check=False,
        )
        passed = completed.returncode == 0
        receipts.append(
            {
                "check_index": index,
                "command_digest": _digest(command),
                "return_code": completed.returncode,
                "passed": passed,
                "elapsed_ms": int((time.monotonic() - started) * 1000),
                "output_recorded": False,
                "content_free": True,
            }
        )
        if not passed:
            failure = (completed.stderr or completed.stdout or "verification_failed")[-1200:]
            break
    return receipts, failure


def _failure_code(error: Exception) -> str:
    code = str(getattr(error, "code", "") or "").strip().casefold()
    if code:
        return re.sub(r"[^a-z0-9_.-]+", "_", code)[:80]
    if isinstance(error, json.JSONDecodeError):
        return "provider_output_not_json"
    if isinstance(error, ValueError):
        return re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(error))[:80] or "value_error"
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", type(error).__name__)[:80]


def execute_generic_isolated_proposal(
    workspace: str | Path,
    proposal: Mapping[str, Any],
    *,
    provider_generate: Callable[[str], str] | None = None,
    baseline_content_digests: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    root = Path(workspace).resolve(strict=True)
    allowed = _allowed_paths(proposal)
    baseline = (
        source_only_manifest_from_content_digests(root, baseline_content_digests)
        if baseline_content_digests is not None
        else source_only_manifest(root)
    )
    provider = provider_generate or _default_provider
    backup_parent = Path(tempfile.mkdtemp(prefix="eidolon-generic-selfdev-"))
    backup = backup_parent / "Eidolon"
    shutil.copytree(root, backup)
    requests = 0
    prior_failure = ""
    failure_codes: list[str] = []
    all_receipts: list[dict[str, Any]] = []
    try:
        improvement_class = str(proposal.get("improvement_class") or "")
        if improvement_class == "dynamic_symbol_refactoring":
            try:
                existing_paths = [rel for rel in allowed if (root / rel).is_file() and rel.endswith(".py")]
                new_paths = [rel for rel in allowed if not (root / rel).exists() and rel.endswith(".py")]
                if len(existing_paths) != 1 or len(new_paths) != 1:
                    raise ValueError("dynamic_symbol_refactoring_scope_requires_one_source_and_destination")
                selected = [str(x) for x in proposal.get("source_symbols") or () if str(x)]
                if not 2 <= len(selected) <= 8 or len(set(selected)) != len(selected):
                    raise ValueError("dynamic_symbol_refactoring_exact_symbols_invalid")
                source_text = (root / existing_paths[0]).read_text(encoding="utf-8")
                extraction = build_symbol_extraction_changes(
                    source_text,
                    source_path=existing_paths[0],
                    destination_path=new_paths[0],
                    symbols=selected,
                )
                review = _apply_transactionally(
                    root,
                    [
                        {"relative_path": existing_paths[0], "action": "modify", "content": extraction["source_content"]},
                        {"relative_path": new_paths[0], "action": "create", "content": extraction["destination_content"]},
                    ],
                )
                changed = [existing_paths[0], new_paths[0]]
                receipts, failure = _run_checks(root, str(proposal.get("proposal_id") or "proposal"), changed)
                if failure:
                    raise ValueError("dynamic_symbol_refactoring_verification_failed")
                candidate = source_only_manifest(root)
                return {
                    "changed_files": changed,
                    "changed_file_count": len(changed),
                    "change_review": review,
                    "check_receipts": receipts,
                    "checks_passed": True,
                    "candidate_manifest_digest": candidate["source_manifest_digest"],
                    "baseline_manifest_digest": baseline["source_manifest_digest"],
                    "provider_request_count": 0,
                    "repair_attempt_count": 0,
                    "selected_symbols": extraction["symbols"],
                    "injected_dependencies": extraction["dependencies"],
                    "symbol_selection_digest": _digest({"source": existing_paths[0], "destination": new_paths[0], "symbols": extraction["symbols"]}),
                    "transformation_digest": extraction["transformation_digest"],
                    "active_source_unchanged": True,
                    "content_free": True,
                }
            except Exception as error:
                raise GenericSelfDevelopmentError(
                    "dynamic_symbol_refactoring_blocked",
                    provider_request_count=0,
                    failure_codes=[_failure_code(error)],
                ) from error
        if improvement_class.endswith("_boundary_extraction"):
            try:
                existing_paths = [rel for rel in allowed if (root / rel).is_file() and rel.endswith(".py")]
                new_paths = [rel for rel in allowed if not (root / rel).exists() and rel.endswith(".py")]
                if len(existing_paths) != 1 or len(new_paths) != 1:
                    raise ValueError("symbol_refactoring_scope_requires_one_source_and_destination")
                source_text = (root / existing_paths[0]).read_text(encoding="utf-8")
                selection_prompt, inventory = build_symbol_selection_prompt(
                    source_text,
                    proposal,
                    source_path=existing_paths[0],
                    destination_path=new_paths[0],
                )
                requests += 1
                raw = provider(selection_prompt)
                _record_private_provider_output(
                    root, proposal, stage="select_symbols", request_number=requests,
                    prompt=selection_prompt, raw=raw,
                )
                selection = parse_symbol_selection(raw, proposal, inventory)
                extraction = build_symbol_extraction_changes(
                    source_text,
                    source_path=existing_paths[0],
                    destination_path=new_paths[0],
                    symbols=list(selection["symbols"]),
                )
                review = _apply_transactionally(
                    root,
                    [
                        {"relative_path": existing_paths[0], "action": "modify", "content": extraction["source_content"]},
                        {"relative_path": new_paths[0], "action": "create", "content": extraction["destination_content"]},
                    ],
                )
                changed = [existing_paths[0], new_paths[0]]
                receipts, failure = _run_checks(
                    root, str(proposal.get("proposal_id") or "proposal"), changed
                )
                if failure:
                    raise ValueError("symbol_refactoring_verification_failed")
                candidate = source_only_manifest(root)
                return {
                    "changed_files": changed,
                    "changed_file_count": len(changed),
                    "change_review": review,
                    "check_receipts": receipts,
                    "checks_passed": True,
                    "candidate_manifest_digest": candidate["source_manifest_digest"],
                    "baseline_manifest_digest": baseline["source_manifest_digest"],
                    "provider_request_count": requests,
                    "repair_attempt_count": 0,
                    "selected_symbols": extraction["symbols"],
                    "injected_dependencies": extraction["dependencies"],
                    "symbol_selection_digest": selection["selection_digest"],
                    "transformation_digest": extraction["transformation_digest"],
                    "active_source_unchanged": True,
                    "content_free": True,
                }
            except Exception as exc:
                if isinstance(exc, GenericSelfDevelopmentError):
                    raise
                raise GenericSelfDevelopmentError(
                    "symbol_level_refactoring_blocked",
                    provider_request_count=requests,
                    failure_codes=[_failure_code(exc)],
                ) from exc
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                staged = attempt == 2 and failure_codes and failure_codes[-1].startswith("provider_output_")
                if staged:
                    new_paths = [rel for rel in allowed if not (root / rel).exists()]
                    existing_paths = [rel for rel in allowed if (root / rel).is_file()]
                    if len(new_paths) != 1 or not existing_paths:
                        raise ValueError("staged_generation_scope_unsupported")
                    requests += 1
                    created_prompt = _created_file_prompt(
                        root, proposal, new_path=new_paths[0], context_paths=existing_paths
                    )
                    created_raw = provider(created_prompt)
                    _record_private_provider_output(
                        root, proposal, stage="create_helper", request_number=requests,
                        prompt=created_prompt, raw=created_raw,
                    )
                    created_content = _parse_created_file(created_raw, new_paths[0])
                    create_review = _apply_transactionally(
                        root,
                        [{"relative_path": new_paths[0], "action": "create", "content": created_content}],
                    )
                    requests += 1
                    modify_prompt = _prompt(
                        root,
                        proposal,
                        existing_paths,
                        attempt=attempt,
                        prior_failure="Use the newly created helper module and return only exact edits to existing files.",
                    )
                    raw = provider(modify_prompt)
                    _record_private_provider_output(
                        root, proposal, stage="modify_existing", request_number=requests,
                        prompt=modify_prompt, raw=raw,
                    )
                    response = _parse_response(raw)
                    changes, modified = _normalize_provider_edits(root, proposal, existing_paths, response)
                    modify_review = _apply_transactionally(root, changes)
                    changed = new_paths + modified
                    review = create_review + modify_review
                else:
                    requests += 1
                    full_prompt = _prompt(root, proposal, allowed, attempt=attempt, prior_failure=prior_failure)
                    raw = provider(full_prompt)
                    _record_private_provider_output(
                        root, proposal, stage="full_contract", request_number=requests,
                        prompt=full_prompt, raw=raw,
                    )
                    response = _parse_response(raw)
                    changes, changed = _normalize_provider_edits(root, proposal, allowed, response)
                    review = _apply_transactionally(root, changes)
                receipts, failure = _run_checks(root, str(proposal.get("proposal_id") or "proposal"), changed)
                all_receipts.extend({**row, "attempt": attempt} for row in receipts)
                if not failure:
                    candidate = source_only_manifest(root)
                    if candidate["source_manifest_digest"] == baseline["source_manifest_digest"]:
                        raise ValueError("provider_produced_no_manifest_change")
                    return {
                        "changed_files": changed,
                        "changed_file_count": len(changed),
                        "change_review": review,
                        "check_receipts": all_receipts,
                        "checks_passed": True,
                        "candidate_manifest_digest": candidate["source_manifest_digest"],
                        "baseline_manifest_digest": baseline["source_manifest_digest"],
                        "provider_request_count": requests,
                        "repair_attempt_count": attempt - 1,
                        "active_source_unchanged": True,
                        "content_free": True,
                    }
                failure_codes.append("verification_failed")
                prior_failure = "verification_failed: " + failure
            except Exception as exc:
                if isinstance(exc, GenericSelfDevelopmentError):
                    raise
                failure_codes.append(_failure_code(exc))
                prior_failure = f"{type(exc).__name__}: {str(exc)[:500]}"
            if attempt < MAX_ATTEMPTS:
                shutil.rmtree(root)
                shutil.copytree(backup, root)
        blocker = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", prior_failure)[:160]
        raise GenericSelfDevelopmentError(
            "generic_self_development_attempts_exhausted:" + blocker,
            provider_request_count=requests,
            failure_codes=failure_codes,
        )
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        shutil.copytree(backup, root)
        raise
    finally:
        shutil.rmtree(backup_parent, ignore_errors=True)


__all__ = ["GenericSelfDevelopmentError", "execute_generic_isolated_proposal"]
