from __future__ import annotations

"""Corpus A qualification and the write-once qualification table.

This is the only place evaluator-only gold for Corpus A is paired with model output.
The table it produces is frozen by digest and becomes an immutable input to Corpus B
routing; nothing in this module can read Corpus B gold.
"""

from collections import defaultdict
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

from g_route1_contract import ROOT, canonical_digest, digest_file
from g_route3_operational import validate_operational
from g_route3_semantics import validate_fixture_output
from g_route2_normalization import normalize
from g_route3_contract import (QUALIFICATION_TABLE_PATH, RISK_CLASSES, TASK_CLASSES, TIER_ORDER, corpus_path,
                               gold_path, indexed_fixture_gold, json_digest, load_json, load_thresholds)

CONTRACT_VERSION = "g-route3.qualification.v1"
TABLE_SCHEMA = "g-route3.qualification-table.v1"
QUALIFIED, NOT_QUALIFIED, INSUFFICIENT = "qualified", "not_qualified", "insufficient_evidence"


def safe_normalize(raw_output: Any, profile: str) -> dict[str, Any]:
    """Transport normalization that never raises on model output (for example JSON nested too deeply)."""
    try:
        return normalize(raw_output, validator_profile=str(profile))
    except Exception as exc:
        text = raw_output if isinstance(raw_output, str) else ""
        return {"contract_version": "g-route2.transport-normalization.v1", "validator_profile": str(profile),
                "raw_output": raw_output, "raw_sha256": canonical_digest(text), "normalized": False,
                "outcome": f"normalization_error:{type(exc).__name__}", "payload": raw_output,
                "payload_sha256": canonical_digest(text), "wrapper_removed": "", "is_repair": False,
                "semantic_values_changed": False}


def sealable(result: dict[str, Any], *, gate: str) -> dict[str, Any]:
    """A validator result must be recordable. If its parsed copy of the model output cannot be serialized
    (nesting too deep), drop that copy and fail the gate; the raw output is still recorded."""
    try:
        json_digest(result)
        return result
    except (RecursionError, ValueError, TypeError):
        reasons = sorted(set(result.get("reasons") or []) | {"model_output_not_recordable"})
        return {key: value for key, value in result.items() if key in ("contract_version", "validator_contract")} | {
            gate: False, "reasons": reasons, "parsed_output": None, "structural_valid": False,
            "uses_gold": bool(result.get("uses_gold")), "belief_effects": "none"}


def collect_evaluation(fixture: Mapping[str, Any], raw_output: Any,
                       execution_evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Gold-blind part of evaluation, safe for the collection path. Model output cannot make it raise."""
    record = safe_normalize(raw_output, str(fixture["validator_profile"]))
    return {
        "normalization": record,
        "raw_operational_validation": sealable(validate_operational(fixture, raw_output, execution_evidence=execution_evidence),
                                               gate="accepted"),
        "normalized_operational_validation": sealable(validate_operational(fixture, record["payload"],
                                                                           execution_evidence=execution_evidence),
                                                      gate="accepted"),
    }


def attach_semantics(records: Iterable[Mapping[str, Any]], corpus: str) -> list[dict[str, Any]]:
    """Evaluator side: pair each record with gold for its own corpus only."""
    index = indexed_fixture_gold(corpus)
    out = []
    for row in records:
        if not str(row["fixture_id"]).startswith(corpus + "-"):
            raise ValueError("cross_corpus_record_in_scoring")
        fixture, gold = index[row["fixture_id"]]
        evidence = row.get("coding_execution_evidence")
        raw_sem = sealable(validate_fixture_output(fixture, gold, row["raw_output"], execution_evidence=evidence),
                           gate="hard_gate_pass")
        norm_sem = sealable(validate_fixture_output(fixture, gold, row["normalization"]["payload"],
                                                    execution_evidence=evidence), gate="hard_gate_pass")
        out.append({**dict(row), "semantics": {
            "raw_semantic_evaluation": raw_sem, "normalized_semantic_evaluation": norm_sem,
            "raw_false_clean": bool(row["raw_operational_validation"]["accepted"] and not raw_sem["hard_gate_pass"]),
            "normalized_false_clean": bool(row["normalized_operational_validation"]["accepted"]
                                           and not norm_sem["hard_gate_pass"]),
        }})
    return out


def failure_rate_upper_bound(failures: int, trials: int, confidence: float = 0.95) -> float | None:
    """One-sided exact (Clopper-Pearson) upper bound on a binomial failure rate."""
    if trials <= 0:
        return None
    if failures >= trials:
        return 1.0
    alpha = 1.0 - confidence

    def cdf(p: float) -> float:
        return sum(math.comb(trials, k) * p ** k * (1 - p) ** (trials - k) for k in range(failures + 1))

    low, high = 0.0, 1.0
    for _ in range(80):
        mid = (low + high) / 2
        if cdf(mid) > alpha:
            low = mid
        else:
            high = mid
    return round(high, 6)


def qualify(records: Iterable[Mapping[str, Any]], thresholds: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    limits = dict((thresholds or load_thresholds())["qualification"])
    grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in records:
        grouped[(row["task_class"], row["risk_class"], row["model_tier"])].append(row)
    cells = []
    for task in TASK_CLASSES:
        for risk in RISK_CLASSES:
            for tier in TIER_ORDER:
                rows = grouped.get((task, risk, tier), [])
                complete_rows = [r for r in rows if not r.get("infrastructure_failure")
                                 and r.get("returned_model") == r.get("model")]
                infra = len(rows) - len(complete_rows)
                accepted = sum(bool(r["normalized_operational_validation"]["accepted"]) for r in rows)
                correct = sum(bool(r["semantics"]["normalized_semantic_evaluation"]["hard_gate_pass"]) for r in rows)
                false_clean = sum(bool(r["semantics"]["normalized_false_clean"]) for r in rows)
                fixtures = {r["fixture_id"] for r in complete_rows}
                per_fixture = [sum(r["fixture_id"] == f for r in complete_rows) for f in sorted(fixtures)]
                exact_design = (len(complete_rows) == limits["observations_required"]
                                and len(fixtures) == limits["distinct_fixtures_required"]
                                and set(per_fixture) == {limits["repeats_per_fixture"]})
                if infra or not exact_design:
                    verdict = INSUFFICIENT
                elif (accepted >= limits["operational_acceptances_required"]
                      and correct >= limits["semantic_passes_required"]
                      and false_clean <= limits["false_clean_allowed"]):
                    verdict = QUALIFIED
                else:
                    verdict = NOT_QUALIFIED
                failures = len(complete_rows) - correct
                cells.append({
                    "task_class": task, "risk_class": risk, "model_tier": tier, "verdict": verdict,
                    "observations": len(rows), "complete_observations": len(complete_rows),
                    "distinct_fixtures": len(fixtures), "operational_acceptances": accepted,
                    "semantic_passes": correct, "false_clean": false_clean, "infrastructure_failures": infra,
                    "failure_rate_upper_95": failure_rate_upper_bound(max(failures, 0), len(complete_rows)),
                })
    return cells


def routing_lookup(cells: Iterable[Mapping[str, Any]]) -> dict[str, list[str]]:
    table: dict[str, list[str]] = {f"{task}|{risk}": [] for task in TASK_CLASSES for risk in RISK_CLASSES}
    for cell in cells:
        if cell["verdict"] == QUALIFIED:
            table[f"{cell['task_class']}|{cell['risk_class']}"].append(cell["model_tier"])
    return {key: [tier for tier in TIER_ORDER if tier in value] for key, value in table.items()}


def _protected_paths() -> set[str]:
    from g_route3_freeze import ARTIFACTS
    from g_route3_runner import GUARDED_PATHS
    return {str(path).replace("\\", "/") for path in (*ARTIFACTS, *GUARDED_PATHS)}


def audit_record(document: Path, verdict: str, auditor: str, *, run_id: str, score_record_sha256: str) -> dict[str, Any]:
    """Bind the Phase A audit to a document by digest, and the document to the run it audits."""
    if not Path(document).is_file():
        raise FileNotFoundError("qualification_audit_document_missing")
    return {"verdict": verdict, "auditor": auditor, "document_path": str(document),
            "document_sha256": digest_file(document), "run_id": run_id, "score_record_sha256": score_record_sha256}


def verify_audit(audit: Mapping[str, Any], source: Mapping[str, Any] | None = None) -> list[str]:
    reasons = []
    if str(audit.get("verdict")) != "READY":
        reasons.append("qualification_audit_not_ready")
    path = Path(str(audit.get("document_path") or ""))
    if not str(audit.get("document_path") or "") or not path.is_file():
        reasons.append("qualification_audit_document_missing")
        return reasons
    if digest_file(path) != audit.get("document_sha256"):
        reasons.append("qualification_audit_document_digest_mismatch")
    text = path.read_text(encoding="utf-8", errors="replace")
    for key in ("run_id", "score_record_sha256"):
        if not audit.get(key) or str(audit[key]) not in text:
            reasons.append(f"qualification_audit_document_does_not_name_{key}")
    try:
        relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        relative = ""
    if relative and relative in _protected_paths():
        reasons.append("qualification_audit_document_is_a_frozen_artifact")
    if source is not None:
        if audit.get("run_id") != source.get("run_id"):
            reasons.append("qualification_audit_names_a_different_run")
        if audit.get("score_record_sha256") != source.get("score_record_sha256"):
            reasons.append("qualification_audit_names_a_different_score")
    return reasons


def build_table(cells: list[Mapping[str, Any]], *, run_id: str, score_record_sha256: str,
                execution_freeze_binding: str, audit: Mapping[str, Any],
                phase_a_attempts: list[Mapping[str, Any]]) -> dict[str, Any]:
    problems = verify_audit(audit, {"run_id": run_id, "score_record_sha256": score_record_sha256})
    if problems:
        raise ValueError("qualification_audit_invalid:" + ",".join(problems))
    doc = {
        "schema_version": TABLE_SCHEMA, "table_id": "G-ROUTE3-QUALIFICATION-TABLE",
        "source": {"corpus": "A", "corpus_sha256": digest_file(corpus_path("A")),
                   "gold_sha256": digest_file(gold_path("A")), "run_id": run_id,
                   "score_record_sha256": score_record_sha256,
                   "thresholds_sha256": json_digest(load_thresholds()),
                   "execution_freeze_binding": execution_freeze_binding,
                   "phase_a_attempts": [dict(row) for row in phase_a_attempts]},
        "audit": dict(audit),
        "evidence_scale": "pilot",
        "cells": [dict(cell) for cell in cells],
        "routing_lookup": routing_lookup(cells),
        "corpus_b_consulted": False,
        "immutable": True,
    }
    doc["table_sha256"] = json_digest(doc)
    return doc


def verify_table(doc: Mapping[str, Any]) -> dict[str, Any]:
    reasons = []
    body = {k: v for k, v in doc.items() if k != "table_sha256"}
    if doc.get("schema_version") != TABLE_SCHEMA:
        reasons.append("table_schema_mismatch")
    if json_digest(body) != doc.get("table_sha256"):
        reasons.append("table_digest_mismatch")
    if doc.get("corpus_b_consulted") is not False or doc.get("source", {}).get("corpus") != "A":
        reasons.append("table_not_derived_from_corpus_a_alone")
    if routing_lookup(doc.get("cells") or []) != doc.get("routing_lookup"):
        reasons.append("routing_lookup_inconsistent_with_cells")
    if len(doc.get("cells") or []) != 72:
        reasons.append("table_cell_count_mismatch")
    if any(c.get("verdict") not in (QUALIFIED, NOT_QUALIFIED, INSUFFICIENT) for c in doc.get("cells") or []):
        reasons.append("unknown_verdict")
    source = doc.get("source") or {}
    reasons += verify_audit(doc.get("audit") or {}, source)
    for key, path in (("corpus_sha256", corpus_path("A")), ("gold_sha256", gold_path("A"))):
        if source.get(key) != digest_file(path):
            reasons.append(f"table_source_{key}_mismatch")
    if source.get("thresholds_sha256") != json_digest(load_thresholds()):
        reasons.append("table_source_thresholds_sha256_mismatch")
    return {"valid": not reasons, "reasons": reasons, "table_sha256": doc.get("table_sha256")}


def freeze_table(doc: Mapping[str, Any], path: Path = QUALIFICATION_TABLE_PATH) -> str:
    """Write-once. A second write with different content is refused."""
    check = verify_table(doc)
    if not check["valid"]:
        raise ValueError("qualification_table_invalid:" + ",".join(check["reasons"]))
    rendered = json.dumps(dict(doc), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != rendered:
            raise FileExistsError("qualification_table_already_frozen")
        return str(doc["table_sha256"])
    path.write_text(rendered, encoding="utf-8", newline="\n")
    return str(doc["table_sha256"])


def load_frozen_table(path: Path = QUALIFICATION_TABLE_PATH) -> dict[str, Any]:
    doc = load_json(path)
    check = verify_table(doc)
    if not check["valid"]:
        raise ValueError("qualification_table_invalid:" + ",".join(check["reasons"]))
    return doc


__all__ = ["CONTRACT_VERSION", "TABLE_SCHEMA", "QUALIFIED", "NOT_QUALIFIED", "INSUFFICIENT", "audit_record",
           "verify_audit",
           "collect_evaluation", "attach_semantics", "failure_rate_upper_bound", "qualify",
           "routing_lookup", "build_table", "verify_table", "freeze_table", "load_frozen_table"]
