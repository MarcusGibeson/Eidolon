from __future__ import annotations

"""Build and verify the governed read-only review package for completed G-CORROB1-R2.

The completed run remains canonical.  This module verifies that append-only run,
then creates a deterministic review representation with explicit source-file and
record digests.  It never invokes a model, executes an experiment, or grants any
authority to the reviewer.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "tools"), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)

import experiment_review as review  # noqa: E402
import rendered_review_package as rendered  # noqa: E402
import structured_record_rendering as record_rendering  # noqa: E402
from g_corrob1_contract import canonical_digest, digest_file  # noqa: E402
from g_corrob1_provider_envelope import verify_envelope_record  # noqa: E402
from g_corrob1_scorer import score  # noqa: E402
from runtime_data_bootstrap import default_runtime_data_dir  # noqa: E402


CONTRACT_VERSION = "g-corrob1.r2.review-package.1"
PACKAGE_ID = "G-CORROB1-R2-REVIEW"
SELECTOR_ALIAS = "G-CORROB1-R2"
RUN_EXPERIMENT_ID = "G-CORROB1-R2"
EXPECTED_CALLS = 192
EXPECTED_PAIRS = 96
EXTERNAL_INTERPRETATION_MARKERS = (
    "chatgpt's interpretation",
    "marcus's interpretation",
    "astra's causal interpretation",
)
SOURCE_DOCUMENTS = (
    ("design.txt", "design", "Frozen prospective experiment design", "DESIGN.md"),
    ("semantic_contract.txt", "design", "Frozen semantic assessment contract", "SEMANTIC_CONTRACT.md"),
    ("prompt.txt", "prompts", "Frozen blind semantic prompt", "prompt.txt"),
    ("corpus.txt", "corpus", "Frozen 32-item primary and diagnostic corpus", "corpus.json"),
    ("gold.txt", "evidence", "Frozen gold and ambiguity classifications", "gold_candidate.json"),
    ("metrics.txt", "evidence", "Preregistered metrics and denominators", "METRICS.md"),
    ("thresholds.txt", "evidence", "Preregistered gate threshold provenance", "THRESHOLD_PROVENANCE.md"),
    ("abort_rules.txt", "evidence", "Frozen abort and integrity rules", "ABORT_RULES.md"),
)
AUTHORITY = {
    **review.REVIEW_AUTHORITY,
    "source_change_authorized": False,
    "memory_change_authorized": False,
    "provider_change_authorized": False,
    "execution_authorized": False,
    "review_authoritative": False,
}


class ReviewPackageBuildError(RuntimeError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return _sha256_bytes(payload)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReviewPackageBuildError(f"unreadable_json:{path.name}:{type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise ReviewPackageBuildError(f"json_object_required:{path.name}")
    return value


def _verify_seal(record: Mapping[str, Any], field: str) -> None:
    expected = str(record.get(field) or "")
    unsigned = {key: value for key, value in record.items() if key != field}
    if not expected or expected != canonical_digest(json.dumps(unsigned, sort_keys=True, separators=(",", ":"))):
        raise ReviewPackageBuildError(f"sealed_record_digest_mismatch:{field}")


def _runtime_root(value: str | Path | None) -> Path:
    return Path(value).expanduser().resolve() if value is not None else Path(default_runtime_data_dir()).resolve()


def _inside(path: Path, parent: Path) -> bool:
    resolved, base = path.resolve(), parent.resolve()
    return resolved != base and base in resolved.parents and not path.is_symlink()


def _completed_lineage(runtime_root: Path) -> dict[str, Any]:
    receipt_area = runtime_root / "experiment_execution_terminal_receipts"
    candidates: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(receipt_area.glob("*.json")) if receipt_area.is_dir() else []:
        value = _read_json(path)
        if value.get("manifest_id") == RUN_EXPERIMENT_ID and value.get("terminal_state") == "complete":
            candidates.append((path, value))
    if len(candidates) != 1:
        raise ReviewPackageBuildError(f"completed_terminal_receipt_count:{len(candidates)}")
    receipt_path, receipt = candidates[0]
    _verify_seal(receipt, "receipt_sha256")

    run_id = str(receipt.get("run_id") or "")
    authorization_id = str(receipt.get("authorization_id") or "")
    if not re.fullmatch(r"gcorrob1r2_authorized_[A-Za-z0-9]+", run_id):
        raise ReviewPackageBuildError("completed_run_id_invalid")
    if not re.fullmatch(r"gcorrob1exec_auth_[A-Za-z0-9_]+", authorization_id):
        raise ReviewPackageBuildError("authorization_id_invalid")
    run_parent = runtime_root / "experiments" / RUN_EXPERIMENT_ID / "runs"
    run_dir = run_parent / run_id
    if not run_dir.is_dir() or not _inside(run_dir, run_parent):
        raise ReviewPackageBuildError("completed_run_directory_invalid")
    authorization_path = runtime_root / "experiment_execution_authorizations" / RUN_EXPERIMENT_ID / f"{authorization_id}.json"
    if not authorization_path.is_file():
        raise ReviewPackageBuildError("execution_authorization_artifact_missing")
    authorization = _read_json(authorization_path)
    if authorization.get("authorization_id") != authorization_id or authorization.get("manifest_id") != RUN_EXPERIMENT_ID:
        raise ReviewPackageBuildError("execution_authorization_binding_mismatch")
    execution_manifest = authorization.get("execution_manifest")
    if not isinstance(execution_manifest, dict):
        raise ReviewPackageBuildError("execution_manifest_missing")
    manifest_sha = str(authorization.get("execution_manifest_sha256") or "")
    if manifest_sha != _json_digest(execution_manifest):
        raise ReviewPackageBuildError("historical_execution_manifest_digest_mismatch")
    if manifest_sha != receipt.get("execution_manifest_sha256"):
        raise ReviewPackageBuildError("terminal_execution_manifest_binding_mismatch")
    return {
        "receipt_path": receipt_path,
        "receipt": receipt,
        "run_dir": run_dir,
        "authorization_path": authorization_path,
        "authorization": authorization,
        "execution_manifest": execution_manifest,
        "execution_manifest_sha256": manifest_sha,
    }


def _load_records(directory: Path, expected: int, kind: str) -> list[tuple[Path, dict[str, Any]]]:
    paths = sorted(directory.glob("*.json")) if directory.is_dir() else []
    if len(paths) != expected:
        raise ReviewPackageBuildError(f"{kind}_record_count:{len(paths)}")
    rows = []
    for path in paths:
        record = _read_json(path)
        _verify_seal(record, "record_sha256")
        rows.append((path, record))
    return rows


def validate_completed_run(source_root: str | Path = ROOT, runtime_root: str | Path | None = None) -> dict[str, Any]:
    """Verify the completed canonical run without comparing it to mutable post-run source."""
    source = Path(source_root).resolve()
    runtime = _runtime_root(runtime_root)
    lineage = _completed_lineage(runtime)
    run_dir = lineage["run_dir"]
    run_path, score_path = run_dir / "run.json", run_dir / "score.json"
    run, stored_score = _read_json(run_path), _read_json(score_path)
    receipt = lineage["receipt"]
    if _sha256_file(run_path) != receipt.get("run_manifest_sha256"):
        raise ReviewPackageBuildError("terminal_run_manifest_digest_mismatch")
    if _sha256_file(score_path) != receipt.get("score_record_sha256"):
        raise ReviewPackageBuildError("terminal_score_digest_mismatch")
    expected_run = {
        "state": "complete", "valid_verdict": True, "belief_effects": "none",
        "calls_persisted": EXPECTED_CALLS, "provider_contacts": EXPECTED_CALLS,
        "returned_responses": EXPECTED_CALLS, "provider_envelopes_persisted": EXPECTED_CALLS,
        "pairs_persisted": EXPECTED_PAIRS, "intended_calls": EXPECTED_CALLS, "intended_pairs": EXPECTED_PAIRS,
    }
    if any(run.get(key) != value for key, value in expected_run.items()):
        raise ReviewPackageBuildError("completed_run_terminal_contract_mismatch")
    if run.get("execution_manifest_sha256") != lineage["execution_manifest_sha256"]:
        raise ReviewPackageBuildError("run_execution_manifest_binding_mismatch")

    calls_with_paths = _load_records(run_dir / "calls", EXPECTED_CALLS, "call")
    pairs_with_paths = _load_records(run_dir / "pairs", EXPECTED_PAIRS, "pair")
    envelopes_with_paths = _load_records(run_dir / "provider_envelopes", EXPECTED_CALLS, "provider_envelope")
    calls = [row for _, row in calls_with_paths]
    pairs = [row for _, row in pairs_with_paths]
    envelopes = [row for _, row in envelopes_with_paths]
    envelope_by_call = {str(row.get("call_id")): row for row in envelopes}
    if len(envelope_by_call) != EXPECTED_CALLS:
        raise ReviewPackageBuildError("provider_envelope_call_identity_mismatch")
    for call in calls:
        call_id = str(call.get("call_id") or "")
        envelope = envelope_by_call.get(call_id)
        if envelope is None:
            raise ReviewPackageBuildError(f"provider_envelope_missing:{call_id}")
        # The append-only envelope record owns the raw bytes/envelope while the
        # linked call record owns deterministic extraction and its raw-response
        # compatibility alias.  Verify the combined historical contract without
        # rewriting either canonical record.
        check = verify_envelope_record({
            **envelope,
            "output_extraction": call.get("output_extraction"),
            "extracted_model_output": call.get("extracted_model_output"),
            "raw_response": call.get("raw_response"),
        })
        if not check.get("valid"):
            raise ReviewPackageBuildError(f"provider_envelope_invalid:{call_id}:{','.join(check.get('reasons') or [])}")
        if (call.get("provider_envelope_record_sha256") != envelope.get("record_sha256")
                or call.get("provider_envelope_sha256") != envelope.get("provider_envelope_sha256")
                or call.get("raw_provider_envelope_sha256") != envelope.get("raw_provider_envelope_sha256")):
            raise ReviewPackageBuildError(f"call_provider_envelope_binding_mismatch:{call_id}")

    gold = _read_json(source / "experiments" / "G-CORROB1-candidate-r2" / "gold_candidate.json")
    recomputed = score(calls, pairs, gold.get("items") or [])
    _verify_seal(stored_score, "report_sha256")
    unsigned_score = {key: value for key, value in stored_score.items() if key != "report_sha256"}
    if recomputed != unsigned_score:
        raise ReviewPackageBuildError("stored_scorer_report_recomputation_mismatch")

    frozen_artifacts = lineage["execution_manifest"].get("artifacts") or {}
    frozen_sources = {}
    for rel in (
        "experiments/G-CORROB1-candidate-r2/corpus.json",
        "experiments/G-CORROB1-candidate-r2/gold_candidate.json",
        "experiments/G-CORROB1-candidate-r2/prompt.txt",
        "experiments/G-CORROB1-candidate-r2/sampling_proposal.json",
        "experiments/G-CORROB1-candidate-r2/METRICS.md",
        "experiments/G-CORROB1-candidate-r2/THRESHOLD_PROVENANCE.md",
        "experiments/G-CORROB1-candidate-r2/ABORT_RULES.md",
    ):
        path = source / rel
        expected = str(frozen_artifacts.get(rel) or "")
        actual = digest_file(path)
        if not expected or actual != expected:
            raise ReviewPackageBuildError(f"frozen_experiment_source_digest_mismatch:{rel}")
        frozen_sources[rel] = {"frozen_sha256": expected, "raw_file_sha256": _sha256_file(path)}

    return {
        **lineage, "source_root": source, "runtime_root": runtime, "run": run, "score": stored_score,
        "calls_with_paths": calls_with_paths, "pairs_with_paths": pairs_with_paths,
        "envelopes_with_paths": envelopes_with_paths, "frozen_sources": frozen_sources,
    }


def _relative_runtime(path: Path, runtime_root: Path) -> str:
    return path.resolve().relative_to(runtime_root.resolve()).as_posix()


def _run_inventory(run_dir: Path) -> list[dict[str, Any]]:
    return [
        {"path": path.relative_to(run_dir).as_posix(), "bytes": path.stat().st_size, "sha256": _sha256_file(path)}
        for path in sorted(run_dir.rglob("*")) if path.is_file() and not path.is_symlink()
    ]


def _call_projection(path: Path, record: Mapping[str, Any], run_dir: Path) -> dict[str, Any]:
    request = record.get("request") or {}
    extraction = record.get("output_extraction") or {}
    preserved = {
        "call_id": record.get("call_id"), "pair_id": record.get("pair_id"), "item_id": record.get("item_id"),
        "repeat": record.get("repeat"), "role": record.get("role"), "ordinal": record.get("ordinal"),
        "pair_ordinal": record.get("pair_ordinal"), "seed": record.get("seed"),
        "raw_response": record.get("raw_response"), "assessment": record.get("assessment"),
        "parse_error": record.get("parse_error"), "validation": record.get("validation"),
        "disposition": record.get("disposition"), "rule": record.get("rule"),
        "rules_fired": record.get("rules_fired"), "reason": record.get("reason"),
        "output_extraction": {
            "status": extraction.get("status"), "selected_field": extraction.get("selected_field"),
            "method": extraction.get("method"), "reasons": extraction.get("reasons"),
            "field_digests": extraction.get("field_digests"), "extraction_sha256": extraction.get("extraction_sha256"),
        },
        "request_identity": {
            "prompt_sha256": request.get("prompt_sha256"),
            "submitted_body_sha256": request.get("submitted_body_sha256"),
            "model": request.get("model"), "seed": request.get("seed"),
            "fresh_session_required": request.get("fresh_session_required"),
        },
        "provider_contacted": record.get("provider_contacted"), "provider_error": record.get("provider_error"),
        "returned_model": record.get("returned_model"), "truncated": record.get("truncated"),
        "prompt_tokens": record.get("prompt_tokens"), "output_tokens": record.get("output_tokens"),
        "token_accounting_available": record.get("token_accounting_available"), "seconds": record.get("seconds"),
        "provider_envelope_record_sha256": record.get("provider_envelope_record_sha256"),
        "provider_envelope_sha256": record.get("provider_envelope_sha256"),
        "raw_provider_envelope_sha256": record.get("raw_provider_envelope_sha256"),
        "submitted_body_sha256": record.get("submitted_body_sha256"),
        "record_sha256": record.get("record_sha256"), "runner_contract": record.get("runner_contract"),
        "belief_effects": record.get("belief_effects"),
    }
    return {
        "source_path": path.relative_to(run_dir).as_posix(),
        "source_file_sha256": _sha256_file(path),
        "record": preserved,
    }


def _pair_projection(path: Path, record: Mapping[str, Any], run_dir: Path) -> dict[str, Any]:
    return {"source_path": path.relative_to(run_dir).as_posix(), "source_file_sha256": _sha256_file(path),
            "canonical_record_sha256": record.get("record_sha256"), "record": dict(record)}


def _review_documents(validated: Mapping[str, Any], staging: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source = Path(validated["source_root"])
    run_dir = Path(validated["run_dir"])
    runtime = Path(validated["runtime_root"])
    candidate = source / "experiments" / "G-CORROB1-candidate-r2"
    staging.mkdir(parents=True, exist_ok=True)

    calls = [_call_projection(path, row, run_dir) for path, row in validated["calls_with_paths"]]
    pairs = [_pair_projection(path, row, run_dir) for path, row in validated["pairs_with_paths"]]
    bindings = {
        "contract_version": CONTRACT_VERSION,
        "canonical_experiment_id": RUN_EXPERIMENT_ID,
        "review_package_id": PACKAGE_ID,
        "completed_run_reference": _relative_runtime(run_dir, runtime),
        "terminal_receipt_reference": _relative_runtime(validated["receipt_path"], runtime),
        "terminal_receipt_sha256": validated["receipt"].get("receipt_sha256"),
        "terminal_receipt_file_sha256": _sha256_file(validated["receipt_path"]),
        "run_manifest_sha256": _sha256_file(run_dir / "run.json"),
        "score_record_sha256": _sha256_file(run_dir / "score.json"),
        "execution_manifest_sha256": validated["execution_manifest_sha256"],
        "corpus_sha256": validated["frozen_sources"]["experiments/G-CORROB1-candidate-r2/corpus.json"]["frozen_sha256"],
        "gold_sha256": validated["frozen_sources"]["experiments/G-CORROB1-candidate-r2/gold_candidate.json"]["frozen_sha256"],
        "prompt_sha256": validated["frozen_sources"]["experiments/G-CORROB1-candidate-r2/prompt.txt"]["frozen_sha256"],
        "model": {
            "provider": validated["run"].get("preflight", {}).get("provider"),
            "provider_version": validated["run"].get("preflight", {}).get("provider_version"),
            "requested": validated["run"].get("preflight", {}).get("requested_model"),
            "resolved": validated["run"].get("preflight", {}).get("resolved_model"),
            "content_digest": validated["run"].get("preflight", {}).get("model_content_digest"),
            "submitted_parameters": validated["run"].get("preflight", {}).get("submitted_parameters"),
            "honoring_attestation": validated["run"].get("preflight", {}).get("honoring_attestation"),
            "silent_fallback": validated["run"].get("preflight", {}).get("silent_fallback"),
        },
        "counts": {"calls": EXPECTED_CALLS, "pairs": EXPECTED_PAIRS, "provider_envelopes": EXPECTED_CALLS},
        "representation": {
            "canonical_artifacts_are_unchanged": True,
            "generated_documents_are_review_representations": True,
            "call_projection_policy": (
                "Preserve exact semantic output, parsed assessment, validation, governance, binding, request and "
                "provider digests, model identity, token/runtime facts and source-record digest; omit only bulky "
                "provider bytes/envelope and duplicated request/metric representations."
            ),
            "canonical_run_inventory_is_complete": True,
            "renderer": rendered.PACKAGE_CONTRACT,
            "structured_rendering": record_rendering.RENDERING_ID,
            "package_builder_source": {
                "path": "tools/g_corrob1_review_package.py",
                "sha256": digest_file(source / "tools" / "g_corrob1_review_package.py"),
            },
            "renderer_source": {
                "path": "tools/rendered_review_package.py",
                "sha256": digest_file(source / "tools" / "rendered_review_package.py"),
            },
            "structured_renderer_source": {
                "path": "tools/structured_record_rendering.py",
                "sha256": digest_file(source / "tools" / "structured_record_rendering.py"),
            },
            "governed_selector_source": {
                "path": "conscious_agent/conversational_experiment_review.py",
                "sha256": digest_file(source / "conscious_agent" / "conversational_experiment_review.py"),
                "selector_alias": SELECTOR_ALIAS,
            },
        },
        "authority": AUTHORITY,
        "belief_effects": "none",
    }
    generated = {
        "run.json": validated["run"],
        "score.json": validated["score"],
        "terminal_receipt.json": validated["receipt"],
        "execution_authorization.json": validated["authorization"],
        "calls_review_projection.json": {
            "contract_version": CONTRACT_VERSION,
            "projection_schema": {
                "preserved": (
                    "Exact semantic output, parsed assessment, validation, governance, binding, request/provider "
                    "digests, model identity, token/runtime facts, and canonical source-record digest."
                ),
                "omitted_duplicates": [
                    "provider_envelope", "raw_provider_envelope_b64", "extracted_model_output_duplicate_of_raw_response",
                    "full_request_duplicate_options_bound_by_submitted_body_sha256",
                    "metrics_duplicate_of_token_and_duration_fields",
                ],
                "provider_envelopes_remain_bound_by": (
                    "provider_envelope_record_sha256, provider_envelope_sha256, raw_provider_envelope_sha256, "
                    "and the complete canonical run inventory"
                ),
            },
            "records": calls,
        },
        "pairs_review_projection.json": {"contract_version": CONTRACT_VERSION, "records": pairs},
        "canonical_lineage.json": {**bindings, "run_inventory": _run_inventory(run_dir)},
    }
    for name, value in generated.items():
        (staging / name).write_text(json.dumps(value, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")

    documents = [
        {"path": package_name, "role": role, "description": description,
         "source": candidate / source_name, "title": description}
        for package_name, role, description, source_name in SOURCE_DOCUMENTS
    ]
    documents += [
        {"path": "run.txt", "role": "evidence", "description": "Exact completed run manifest", "source": staging / "run.json", "title": "Completed run manifest"},
        {"path": "score.txt", "role": "scorer", "description": "Exact frozen deterministic scorer output", "source": staging / "score.json", "title": "Frozen scorer output"},
        {"path": "terminal_receipt.txt", "role": "evidence", "description": "Exact terminal execution receipt", "source": staging / "terminal_receipt.json", "title": "Terminal receipt"},
        {"path": "execution_authorization.txt", "role": "evidence", "description": "Historical execution manifest and authorization", "source": staging / "execution_authorization.json", "title": "Execution authorization"},
        {"path": "calls.txt", "role": "raw_outputs", "description": "Digest-bound per-call semantic and governance records", "source": staging / "calls_review_projection.json", "title": "Call records"},
        {"path": "pairs.txt", "role": "raw_outputs", "description": "Digest-bound A/B pair and comparator records", "source": staging / "pairs_review_projection.json", "title": "Pair records"},
        {"path": "canonical_lineage.txt", "role": "evidence", "description": "Complete canonical-run inventory, bindings, and review boundaries", "source": staging / "canonical_lineage.json", "title": "Canonical lineage"},
    ]
    return documents, {"generated": generated, "bindings": bindings}


def _manifest_fields(validated: Mapping[str, Any], bindings: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "selector_aliases": [SELECTOR_ALIAS],
        "review_package_contract": CONTRACT_VERSION,
        "canonical_bindings": dict(bindings),
        "non_authoritative": True,
        "authority": AUTHORITY,
        "belief_effects": "none",
        "source_run_reference": bindings["completed_run_reference"],
        "renderer_version": rendered.PACKAGE_CONTRACT,
        "package_format": record_rendering.RENDERING_ID,
        "historical_execution_manifest_note": (
            "The embedded execution manifest is verified against its historical digest. Post-run source changes are "
            "not reinterpreted as changes to the completed canonical experiment."
        ),
    }


def _rendered_json(package_dir: Path, name: str) -> Any:
    text = (package_dir / name).read_text(encoding="utf-8")
    if "\n\n" not in text:
        raise ReviewPackageBuildError(f"rendered_document_header_missing:{name}")
    return record_rendering.reconstruct(text.split("\n\n", 1)[1])


def verify_review_package(package_dir: str | Path, *, source_root: str | Path = ROOT,
                          runtime_root: str | Path | None = None) -> dict[str, Any]:
    package_path = Path(package_dir).resolve()
    validated = validate_completed_run(source_root, runtime_root)
    loaded = review.load_package(package_path)
    manifest = loaded["manifest"]
    if loaded["experiment_id"] != PACKAGE_ID or manifest.get("selector_aliases") != [SELECTOR_ALIAS]:
        raise ReviewPackageBuildError("review_package_selector_identity_mismatch")
    if manifest.get("canonical_experiment_id") != RUN_EXPERIMENT_ID:
        raise ReviewPackageBuildError("review_package_canonical_identity_mismatch")
    if manifest.get("non_authoritative") is not True or manifest.get("belief_effects") != "none":
        raise ReviewPackageBuildError("review_package_authority_boundary_missing")
    if any(value is not False for value in (manifest.get("authority") or {}).values()):
        raise ReviewPackageBuildError("review_package_authority_not_fully_denied")

    with tempfile.TemporaryDirectory(prefix="g-corrob1-review-verify-") as temp:
        _docs, expected = _review_documents(validated, Path(temp))
        mapping = {
            "run.txt": "run.json", "score.txt": "score.json", "terminal_receipt.txt": "terminal_receipt.json",
            "execution_authorization.txt": "execution_authorization.json", "calls.txt": "calls_review_projection.json",
            "pairs.txt": "pairs_review_projection.json", "canonical_lineage.txt": "canonical_lineage.json",
        }
        for package_name, generated_name in mapping.items():
            if _rendered_json(package_path, package_name) != expected["generated"][generated_name]:
                raise ReviewPackageBuildError(f"review_representation_drift:{package_name}")
    lowered = "\n".join(path.read_text(encoding="utf-8", errors="replace").casefold()
                           for path in package_path.iterdir() if path.is_file())
    if any(marker in lowered for marker in EXTERNAL_INTERPRETATION_MARKERS):
        raise ReviewPackageBuildError("external_interpretation_present")
    return {
        "valid": True, "package_id": PACKAGE_ID, "selector_alias": SELECTOR_ALIAS,
        "manifest_sha256": loaded["manifest_sha256"], "documents": len(loaded["documents"]),
        "parts": sum(len(review.chunks(row["text"])) for row in loaded["documents"]),
        "characters": sum(len(row["text"]) for row in loaded["documents"]),
        "provider_calls": 0, "review_launches": 0, "experiment_launches": 0, "belief_effects": "none",
    }


def _tree_digest(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): _sha256_file(path) for path in sorted(root.rglob("*")) if path.is_file()}


def build_and_install(*, source_root: str | Path = ROOT, runtime_root: str | Path | None = None) -> dict[str, Any]:
    source, runtime = Path(source_root).resolve(), _runtime_root(runtime_root)
    validated = validate_completed_run(source, runtime)
    area = runtime / "research_packages"
    area.mkdir(parents=True, exist_ok=True)
    target = area / PACKAGE_ID
    with tempfile.TemporaryDirectory(prefix=".g-corrob1-review-", dir=area) as temp_name:
        work = Path(temp_name)
        sources, package_stage = work / "sources", work / "package"
        documents, generated = _review_documents(validated, sources)
        rendered.build(
            documents, out_dir=package_stage, experiment_id=PACKAGE_ID,
            title="G-CORROB1-R2 completed frozen experiment - independent review package",
            brief=("Review the completed frozen experiment independently using only the canonical facts and their "
                   "deterministic review representations. All review conclusions remain non-authoritative."),
            canonical_experiment_id=RUN_EXPERIMENT_ID,
        )
        manifest_path = package_stage / review.MANIFEST_NAME
        manifest = _read_json(manifest_path)
        manifest.update(_manifest_fields(validated, generated["bindings"]))
        manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
        verification = verify_review_package(package_stage, source_root=source, runtime_root=runtime)
        if target.exists():
            if not target.is_dir() or _tree_digest(target) != _tree_digest(package_stage):
                raise ReviewPackageBuildError("installed_review_package_conflict_or_drift")
            installed = False
        else:
            os.replace(package_stage, target)
            installed = True
    final = verify_review_package(target, source_root=source, runtime_root=runtime)
    return {
        **final, "installed": installed, "location": str(target),
        "source_run_reference": final and _relative_runtime(validated["run_dir"], runtime),
        "terminal_receipt_sha256": validated["receipt"].get("receipt_sha256"),
        "execution_manifest_sha256": validated["execution_manifest_sha256"],
        "model_digest": validated["run"].get("preflight", {}).get("model_content_digest"),
        "artifacts_included": [spec[0] for spec in SOURCE_DOCUMENTS] + [
            "run.txt", "score.txt", "terminal_receipt.txt", "execution_authorization.txt", "calls.txt",
            "pairs.txt", "canonical_lineage.txt",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build/install the governed G-CORROB1-R2 review package; no model calls.")
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--source-root", default=str(ROOT))
    parser.add_argument("--verify", default="", help="verify an existing package directory instead of installing")
    args = parser.parse_args()
    if args.verify:
        result = verify_review_package(args.verify, source_root=args.source_root, runtime_root=args.runtime_root or None)
    else:
        result = build_and_install(source_root=args.source_root, runtime_root=args.runtime_root or None)
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
