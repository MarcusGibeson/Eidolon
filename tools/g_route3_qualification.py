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

from g_route1_contract import digest_file
from g_route3_operational import validate_operational
from g_route1_validators import validate_fixture_output
from g_route2_normalization import normalize
from g_route3_contract import (QUALIFICATION_TABLE_PATH, RISK_CLASSES, TASK_CLASSES, TIER_ORDER, corpus_path,
                               gold_path, indexed_fixture_gold, json_digest, load_json, load_thresholds)

CONTRACT_VERSION = "g-route3.qualification.v1"
TABLE_SCHEMA = "g-route3.qualification-table.v1"
QUALIFIED, NOT_QUALIFIED, INSUFFICIENT = "qualified", "not_qualified", "insufficient_evidence"


def collect_evaluation(fixture: Mapping[str, Any], raw_output: Any,
                       execution_evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Gold-blind part of evaluation, safe for the collection path."""
    record = normalize(raw_output, validator_profile=str(fixture["validator_profile"]))
    return {
        "normalization": record,
        "raw_operational_validation": validate_operational(fixture, raw_output, execution_evidence=execution_evidence),
        "normalized_operational_validation": validate_operational(fixture, record["payload"],
                                                                  execution_evidence=execution_evidence),
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
        raw_sem = validate_fixture_output(fixture, gold, row["raw_output"], execution_evidence=evidence)
        norm_sem = validate_fixture_output(fixture, gold, row["normalization"]["payload"], execution_evidence=evidence)
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


def audit_record(document: Path, verdict: str, auditor: str) -> dict[str, Any]:
    """Bind the Phase A audit to a file by digest. A bare dictionary saying READY is not an audit."""
    if not Path(document).is_file():
        raise FileNotFoundError("qualification_audit_document_missing")
    return {"verdict": verdict, "auditor": auditor, "document_path": str(document),
            "document_sha256": digest_file(document)}


def verify_audit(audit: Mapping[str, Any]) -> list[str]:
    reasons = []
    if str(audit.get("verdict")) != "READY":
        reasons.append("qualification_audit_not_ready")
    path = Path(str(audit.get("document_path") or ""))
    if not path.is_file():
        reasons.append("qualification_audit_document_missing")
    elif digest_file(path) != audit.get("document_sha256"):
        reasons.append("qualification_audit_document_digest_mismatch")
    return reasons


def build_table(cells: list[Mapping[str, Any]], *, run_id: str, score_record_sha256: str,
                execution_freeze_binding: str, audit: Mapping[str, Any],
                phase_a_attempts: list[Mapping[str, Any]]) -> dict[str, Any]:
    problems = verify_audit(audit)
    if problems:
        raise ValueError("qualification_audit_invalid:" + ",".join(problems))
    doc = {
        "schema_version": TABLE_SCHEMA, "table_id": "G-ROUTE3-QUALIFICATION-TABLE-R1",
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
    reasons += verify_audit(doc.get("audit") or {})
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
