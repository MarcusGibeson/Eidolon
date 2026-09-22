from __future__ import annotations

"""Reviewer capacity qualification: can the frozen reviewer (v2731.8) be qualified above 27 parts?

This tests the REVIEWER, not any experiment. It builds synthetic packages at a chosen part count, drives the real
``experiment_review.review_experiment`` through a deterministic stub model, and measures what survives at each level.

Nothing here reads, imports or depends on G-EVID1. The synthetic corpus is generated deterministically and describes a
made-up experiment (Q-CAP) whose records are mechanically checkable: every record line carries a unique ``ref=`` token,
so observation loss, citation relocatability and document-boundary correctness can be checked by construction rather
than by reading anything.

The stub is calibrated against the reviewer's own measured behaviour on a completed real review (G-INVAR, 19 parts:
100 grounded observations, 45 part statements, 20 carried to document level, 30 document statements, 22 carried to
final, 52 final inputs, 7,800 final input characters). Calibration fixes the stub's observation count and citation
rates; it is deliberately NOT tuned per part count, and a sensitivity sweep runs the same structure at optimistic and
pessimistic citation rates so a capacity result cannot be an artefact of one stub setting.
"""

import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)

import experiment_review as er  # noqa: E402

# Measured from the completed G-INVAR review (19 required parts). Calibrates the stub; never tunes the reviewer.
CALIBRATION = {
    "source": "G-INVAR review 72a40f4dc8a09ae3", "parts": 19, "grounded_observations": 100,
    "part_statements": 45, "carried_to_document": 20, "document_statements": 30, "carried_to_final": 22,
    "final_inputs": 52, "final_input_chars": 7800,
}
OBS_PER_PART = 5              # 100 grounded observations / 19 parts
PART_CITE_RATE = 0.80         # share of a part unit's observations that get cited (20 of 100 carried forward)
DOC_CITE_RATE = 0.66          # share of a document unit's inputs that get cited (22 of 65 carried forward)
STATEMENTS_PER_INPUT = 0.45   # 45 statements / 100 observations at the part level, 30 / 65 at the document level
IDS_PER_STATEMENT = 2         # 45 statements covering ~80 cited observations
STATEMENT_WORDS = 16          # tuned so a rendered final input line averages the measured ~150 characters

# Sensitivity band: the same structure run with a more and a less compressive model, so a capacity verdict cannot be
# an artefact of one stub setting.
SENSITIVITY = {
    "optimistic": {"statements_per_input": 0.60, "ids_per_statement": 4, "statement_words": 12},
    "nominal": {},
    "pessimistic": {"statements_per_input": 0.25, "ids_per_statement": 1, "statement_words": 20},
}

# The part shape of each qualification scale. The 34-part shape mirrors the document structure the reviewer must
# handle in normal operation: six roles, one dominant machine-generated document.
SHAPES = {
     6: (1, 1, 1, 1, 1, 1),   # the smallest well-formed package: one part per role, for fast live smoke tests
    16: (2, 1, 2, 4, 4, 3),   # the bounded live smoke-test scale: smallest that still needs a consolidation round
    19: (2, 1, 2, 4, 7, 3),   # the calibration scale: the size of the completed G-INVAR review
    27: (3, 1, 3, 6, 11, 3),  # the demonstrated v2731.8 ceiling
    28: (3, 1, 3, 7, 11, 3),
    30: (3, 1, 3, 8, 12, 3),
    32: (3, 1, 3, 8, 14, 3),
    34: (3, 1, 3, 8, 16, 3),  # the scale of the unchanged G-EVID1 package
    48: (4, 1, 4, 11, 23, 5),
    64: (5, 1, 5, 15, 31, 7),
   140: (9, 2, 9, 34, 68, 18),  # the scale of the G-CORROB1-R2 review package

}
DOCS = (
    ("design.md", "design", "Q-CAP synthetic design note"),
    ("prompts.txt", "prompts", "Q-CAP synthetic prompt template"),
    ("corpus.txt", "corpus", "Q-CAP synthetic corpus records"),
    ("raw_outputs.txt", "raw_outputs", "Q-CAP synthetic raw outputs"),
    ("scorer_report.txt", "scorer", "Q-CAP synthetic scorer records"),
    ("evidence.txt", "evidence", "Q-CAP synthetic labels"),
)
WORDS = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa quebec "
         "romeo sierra tango uniform victor whiskey xray yankee zulu").split()


# --- synthetic content ---------------------------------------------------------------------------------------------
def _filler(seed: int, count: int) -> str:
    return " ".join(WORDS[(seed * 7 + i * 13) % len(WORDS)] for i in range(count))


def _record(doc_key: str, n: int) -> str:
    """One mechanically checkable record line: a unique ref token, record metadata, and filler prose."""
    ref = f"{doc_key.upper()}R{n:04d}"
    return f"ref={ref} item=S{n % 400:03d} run={n % 3 + 1} field={WORDS[n % len(WORDS)]} note: {_filler(n, 14)}"


def _document_text(doc_key: str, role: str, parts: int) -> str:
    """Generate text whose deterministic chunking yields exactly ``parts`` parts, filled close to the chunk limit."""
    target = (parts - 1) * er.CHUNK_CHARS + int(er.CHUNK_CHARS * 0.78)
    head = f"Q-CAP synthetic {role} document. Every record line carries a unique ref token.\n"
    lines, n = [head], 0
    while sum(len(x) for x in lines) < target:
        n += 1
        lines.append(_record(doc_key, n) + "\n")
    text = "".join(lines)
    while len(er.chunks(text)) > parts and len(lines) > 2:
        lines.pop()
        text = "".join(lines)
    while len(er.chunks(text)) < parts:
        n += 1
        lines.append(_record(doc_key, n) + "\n")
        text = "".join(lines)
    return text


def build_package(out_dir: Path, parts_target: int) -> dict[str, Any]:
    """Write a synthetic package whose total chunk count is exactly ``parts_target``."""
    if parts_target not in SHAPES:
        raise ValueError(f"no shape defined for {parts_target} parts")
    out_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    total_chars = total_parts = 0
    for (name, role, description), parts in zip(DOCS, SHAPES[parts_target]):
        text = _document_text(name.split(".")[0], role, parts)
        (out_dir / name).write_text(text, encoding="utf-8", newline="\n")
        if len(er.chunks(text)) != parts:
            raise AssertionError(f"{name}: wanted {parts} parts, produced {len(er.chunks(text))}")
        total_chars += len(text)
        total_parts += parts
        entries.append({"doc_id": f"D{len(entries) + 1}", "path": name, "role": role, "description": description,
                        "sha256": hashlib.sha256((out_dir / name).read_bytes()).hexdigest()})
    (out_dir / er.MANIFEST_NAME).write_text(json.dumps({
        "experiment_id": f"Q-CAP{parts_target}",
        "title": f"Q-CAP{parts_target} - synthetic reviewer capacity qualification package",
        "task": "independent_review",
        "brief": "Synthetic package used to qualify reviewer capacity. It carries no real experimental meaning.",
        "documents": entries}, indent=1), encoding="utf-8", newline="\n")
    return {"dir": out_dir, "parts": total_parts, "chars": total_chars, "documents": len(entries)}


# --- the deterministic stub model ----------------------------------------------------------------------------------
_CHUNK = re.compile(r"part (\d+) of (\d+)\.\n---\n(.*)\n---\n", re.S)
# Every id the hierarchy can present to a synthesis level: observations, part, document and group statements, and
# uncaptured registers. Missing one starves that level of citable inputs and makes consolidation look far worse than
# it is, which is exactly the artefact this regex caused before GS and U were added.
_INPUT_ID = re.compile(r"^(O\d+|PS\d+|DS\d+|GS\d+|U\d+)\b", re.M)


def _statement(seed: int, words: int = 12) -> str:
    """Plain prose with no digits or identifiers, so it can never fail the unsupported-identifier check."""
    return "the record shows " + _filler(seed, words)


def deterministic_stub(*, part_cite_rate: float = PART_CITE_RATE, doc_cite_rate: float = DOC_CITE_RATE,
                       obs_per_part: int = OBS_PER_PART,
                       statements_per_input: float = STATEMENTS_PER_INPUT,
                       ids_per_statement: int = IDS_PER_STATEMENT,
                       statement_words: int = STATEMENT_WORDS) -> Callable[[str, int], tuple[str, dict[str, Any]]]:
    """A model that always answers in the requested shape, quoting real spans. No randomness anywhere."""

    def reply(payload: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
        text = json.dumps(payload, ensure_ascii=False)
        return text, {"metrics": {"prompt_eval_count": 0, "eval_count": max(1, len(text) // 3)}}

    def call_model(prompt: str, max_tokens: int) -> tuple[str, dict[str, Any]]:
        if '"observations"' in prompt and '"open_questions"' in prompt:
            match = _CHUNK.search(prompt)
            chunk = match.group(3) if match else ""
            lines = [line for line in chunk.split("\n") if len(line) >= er.MIN_QUOTE_CHARS + 20]
            observations = []
            if lines:
                step = max(1, len(lines) // max(1, obs_per_part))
                for i in range(min(obs_per_part, len(lines))):
                    line = lines[(i * step) % len(lines)]
                    observations.append({"statement": _statement(i + len(lines)),
                                         "quotes": [line[: er.MAX_QUOTE_CHARS - 1].rstrip()]})
            return reply({"observations": observations, "open_questions": [_statement(1, 6)]})

        if '"statements"' in prompt:
            key = "obs_ids" if '"obs_ids"' in prompt else "input_ids"
            rate = part_cite_rate if key == "obs_ids" else doc_cite_rate
            block = prompt.split("Each has an id and, in brackets")[-1]
            ids = list(dict.fromkeys(_INPUT_ID.findall(block)))
            cap_match = re.search(r"Give at most (\d+) statements", prompt)
            cap = int(cap_match.group(1)) if cap_match else 1
            chosen = ids[: max(1, round(len(ids) * rate))] if ids else []
            # Real models write many short statements citing few inputs each, and they write MORE statements when
            # given more inputs. G-INVAR measured 45 statements over 19 part units of ~5.26 observations (0.45 per
            # input) and 30 statements over 10 document units of ~6.5 inputs (0.46 per input), so one proportional
            # rate reproduces both levels instead of two fixed per-unit counts.
            wanted = min(cap, max(1, round(len(ids) * statements_per_input)))
            statements = []
            for n in range(wanted):
                group = chosen[n * ids_per_statement:(n + 1) * ids_per_statement]
                if not group:
                    break
                statements.append({"statement": _statement(n + len(ids), statement_words),
                                   "kind": "finding", key: group})
            if not statements and chosen:
                statements = [{"statement": _statement(len(ids), statement_words), "kind": "finding",
                               key: chosen[:ids_per_statement]}]
            return reply({"statements": statements})

        ids = list(dict.fromkeys(_INPUT_ID.findall(prompt)))
        head = ids[: er.MAX_IDS_PER_STATEMENT]
        if '"competing_hypotheses"' in prompt:
            return reply({
                "competing_hypotheses": [{"hypothesis": _statement(2), "evidence_for": head[:3],
                                          "evidence_against": head[3:5]}],
                "unknowns": [{"statement": _statement(3), "input_ids": head[:2]}],
                "confidence": {"level": "low", "reason": _statement(4, 8), "input_ids": head[:2]},
                "discriminating_experiments": [{"experiment": _statement(5), "distinguishes": [1],
                                                "input_ids": head[:2]}],
                "not_established": [{"statement": _statement(6), "input_ids": head[:2]}]})
        return reply({
            "experiment_understanding": {"statement": _statement(7), "input_ids": head[:4]},
            "observations": [{"statement": _statement(8), "input_ids": head[:4]}],
            "passed": [{"statement": _statement(9), "input_ids": head[:2]}],
            "failed": [{"statement": _statement(10), "input_ids": head[:2]}],
            "failure_clusters": [{"statement": _statement(11), "input_ids": head[:2]}],
            "possible_harness_or_measurement_failures": [{"statement": _statement(12), "input_ids": head[:2]}],
            "possible_model_or_reasoning_failures": [{"statement": _statement(13), "input_ids": head[:2]}],
            "ambiguous_cases": [{"statement": _statement(14), "input_ids": head[:2]}]})

    return call_model


# --- measurement ----------------------------------------------------------------------------------------------------
def relocatability(artifact: Mapping[str, Any], package_dir: Path) -> dict[str, Any]:
    """Every grounded quote must re-locate byte-exactly in its source document, inside its own part."""
    texts = {d["doc_id"]: (package_dir / d["path"]).read_text(encoding="utf-8")
             for d in artifact["provenance"]["documents"]}
    bounds: dict[tuple[str, int], tuple[int, int]] = {}
    for doc_id, text in texts.items():
        offset = 0
        for part, chunk in enumerate(er.chunks(text), 1):
            bounds[(doc_id, part)] = (offset, offset + len(chunk))
            offset += len(chunk)
    checked = exact = in_part = 0
    failures: list[dict[str, Any]] = []
    for obs in artifact["grounded_observations"]:
        for quote in obs["quotes"]:
            checked += 1
            text = texts[obs["doc_id"]]
            span = text[quote["char_start"]:quote["char_end"]]
            hit = span == quote["text"]
            lo, hi = bounds[(obs["doc_id"], obs["part"])]
            inside = lo <= quote["char_start"] and quote["char_end"] <= hi
            exact += hit
            in_part += inside
            if not (hit and inside):
                failures.append({"obs_id": obs["obs_id"], "doc_id": obs["doc_id"], "part": obs["part"],
                                 "exact": hit, "inside_part": inside})
    return {"quotes_checked": checked, "relocated_exactly": exact, "inside_own_part": in_part,
            "relocatable": checked == exact == in_part, "failures": failures[:10]}


def identifier_validity(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Every id cited anywhere in the hierarchy must exist; nothing may reference an id the review never made."""
    hierarchy = artifact["hierarchy"]
    # Every statement kind the reviewer can mint, including the hierarchical version's group statements and
    # uncaptured registers. Omitting one would report the reviewer as citing identifiers it legitimately created.
    produced = (hierarchy["part_statements"] + hierarchy["document_statements"]
                + hierarchy.get("group_statements", []) + hierarchy.get("uncaptured_registers", []))
    known = {o["obs_id"] for o in artifact["grounded_observations"]} | {s["id"] for s in produced}
    cited: set[str] = set()
    for s in produced:
        cited |= set(s.get("cites") or [])
    cited |= set(hierarchy["final_inputs"])
    return {"known_ids": len(known), "cited_ids": len(cited), "unknown_cited": sorted(cited - known),
            "unknown_references": artifact["unknown_references"], "valid": not (cited - known)}


def measure(artifact: Mapping[str, Any], package_dir: Path, seconds: float) -> dict[str, Any]:
    cov, lv = artifact["coverage"], artifact["coverage"]["levels"]
    reloc = relocatability(artifact, package_dir)
    ids = identifier_validity(artifact)
    run = artifact["runtime_accounting"]
    captured = lv["part_synthesis"]["observations_cited"]
    carried = lv["part_synthesis"]["observations_carried_forward"]
    grounded = lv["part_synthesis"]["observations"]
    return {
        "status": artifact["status"],
        "part_coverage": {"required": cov["required_parts"], "reviewed": cov["reviewed_required_parts"],
                          "coverage": cov["required_coverage"], "full": cov["required_coverage"] == 1.0},
        "grounded_observations": grounded,
        "observation_preservation": {"represented": lv["architecture"]["represented_in_final_inputs"],
                                     "coverage": lv["architecture"]["coverage"],
                                     "silently_dropped": lv["architecture"]["silently_dropped"],
                                     "no_silent_loss": not lv["architecture"]["silently_dropped"]},
        "uncaptured_accounting": {"cited_by_part_statements": captured, "carried_forward": carried,
                                  "accounted": captured + carried, "grounded": grounded,
                                  "balances": captured + carried == grounded},
        "relocatability": reloc,
        "identifier_validity": ids,
        "document_boundaries": {"documents": len(artifact["provenance"]["documents"]),
                                "parts_seen": len(cov["parts"]),
                                "correct": reloc["inside_own_part"] == reloc["quotes_checked"]},
        "synthesis": {"part_units": lv["part_synthesis"]["units"],
                      "part_units_accepted": lv["part_synthesis"]["accepted"],
                      "document_units": lv["document_synthesis"]["units"],
                      "document_units_accepted": lv["document_synthesis"]["accepted"],
                      "document_unit_slots": lv["document_synthesis"].get("statement_slots"),
                      "final_first_half": lv["final"]["first_half"], "final_second_half": lv["final"]["second_half"],
                      "complete": (lv["part_synthesis"]["units"] == lv["part_synthesis"]["accepted"]
                                   and lv["document_synthesis"]["units"] == lv["document_synthesis"]["accepted"]
                                   and lv["final"]["first_half"] == "accepted"
                                   and lv["final"]["second_half"] == "accepted")},
        "final_budget": {"inputs": lv["final"]["inputs"], "chars": lv["final"]["input_chars"],
                         "budget": lv["final"]["input_budget"],
                         "used": round(lv["final"]["input_chars"] / lv["final"]["input_budget"], 4),
                         "within": lv["final"]["input_chars"] <= lv["final"]["input_budget"],
                         "bound_inputs": lv["final"].get("input_bound"),
                         "bound_chars": lv["final"].get("input_bound_chars"),
                         "within_bound": (lv["final"]["inputs"] <= lv["final"]["input_bound"]
                                          if lv["final"].get("input_bound") else None)},
        "intermediate": ({"round_count": lv["intermediate_synthesis"]["round_count"],
                          "units": lv["intermediate_synthesis"]["units"],
                          "statements": lv["intermediate_synthesis"]["statements"],
                          "converged": lv["intermediate_synthesis"]["converged"],
                          "rounds": [{k: r[k] for k in ("round", "units", "inputs", "statements", "carried",
                                                        "surviving", "reduction", "accepted")}
                                     for r in lv["intermediate_synthesis"]["rounds"]],
                          "complete": all(r["units"] == r["accepted"]
                                          for r in lv["intermediate_synthesis"]["rounds"])}
                         if "intermediate_synthesis" in lv else None),
        "disagreement_preservation": {"statement_kinds": cov.get("statement_kinds", {}),
                                      "non_finding_kinds": sum(v for k, v in cov.get("statement_kinds", {}).items()
                                                               if k != "finding")},
        "mechanical_verification": {"complete": cov["complete"], "missing": cov["missing"]},
        "mutation_guard": {"passed": artifact["mutation_guard"]["passed"],
                           "source_tree_protected": artifact["mutation_guard"]["protected"]["source_tree"],
                           "changes": artifact["mutation_guard"]["changes"][:5]},
        "tokens": {"prompt": run.get("prompt_tokens"), "output": run.get("output_tokens")},
        # ``grounding_retries`` since retry-accounting.v2; older artifacts still carry the conflated ``retries``.
        "degradation": {"provider_attempts": run["provider_attempts"],
                        "grounding_retries": run.get("grounding_retries", run.get("retries", 0)),
                        "repair_attempts": run.get("repair_attempts", 0),
                        "truncated_attempts": run["truncated_attempts"],
                        "unparseable_or_rejected": run["unparseable_or_rejected_replies"],
                        "failed_attempts": run["failed_attempts"],
                        "stages_without_accepted_reply": run["stages_without_accepted_reply"],
                        "rejections_by_reason": run["rejections_by_reason"]},
        "runtime": {"seconds": round(seconds, 2), "model_calls": run["provider_attempts"]},
    }


def qualify(parts_target: int, *, work_dir: Path, guard_source: bool = True, reviewer: Any = er,
            call_model: Callable[[str, int], tuple[str, dict[str, Any]]] | None = None,
            identity: Mapping[str, Any] | None = None, **stub_kwargs: Any) -> dict[str, Any]:
    """Build a synthetic package at ``parts_target`` and run a reviewer over it.

    ``reviewer`` is the module under qualification: the frozen baseline (``experiment_review``) or the hierarchical
    candidate. ``call_model`` overrides the deterministic stub, which is how the real-model runs are driven.
    """
    import time

    work_dir.mkdir(parents=True, exist_ok=True)
    package_dir = work_dir / f"package-{parts_target}"
    built = build_package(package_dir, parts_target)
    runtime = work_dir / f"runtime-{parts_target}"
    runtime.mkdir(parents=True, exist_ok=True)
    began = time.monotonic()
    artifact = reviewer.review_experiment(
        package_dir, call_model=call_model or deterministic_stub(**stub_kwargs),
        runtime_root_path=runtime, source_root=ROOT if guard_source else None,
        identity=dict(identity) if identity is not None else
        {"model": "deterministic_stub", "provider": "qualification_harness", "context_size": 8192,
         "resolved_config_sha256": "0" * 64})
    seconds = time.monotonic() - began
    settings = {"part_cite_rate": PART_CITE_RATE, "doc_cite_rate": DOC_CITE_RATE, "obs_per_part": OBS_PER_PART,
                "statements_per_input": STATEMENTS_PER_INPUT, "ids_per_statement": IDS_PER_STATEMENT,
                "statement_words": STATEMENT_WORDS}
    settings.update(stub_kwargs)
    return {"parts_target": parts_target,
            "package": {"parts": built["parts"], "chars": built["chars"], "documents": built["documents"]},
            "stub": settings,
            "measurements": measure(artifact, package_dir, seconds),
            "review_id": artifact["review_id"],
            "reviewer": {"contract_version": artifact["contract_version"],
                         "module_sha256": artifact["provenance"]["capability"]["module_sha256"]}}


def sweep(scales: tuple[int, ...] = (19, 28, 30, 32, 34), reviewer: Any = er) -> dict[str, Any]:
    """Run every scale across the sensitivity band. Deterministic: the same inputs give the same numbers."""
    import tempfile

    runs: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="q-cap-sweep-") as tmp:
        for band, kwargs in SENSITIVITY.items():
            for target in scales:
                result = qualify(target, work_dir=Path(tmp) / band / str(target), guard_source=False,
                                 reviewer=reviewer, **kwargs)
                runs.append({"band": band, **result})
    limits = {"chunk_chars": er.CHUNK_CHARS, "final_input_budget_chars": er.FINAL_INPUT_BUDGET_CHARS,
              "document_statement_slots": er.document_statement_slots()}
    if hasattr(reviewer, "registered_limits"):
        limits = dict(reviewer.registered_limits())
    return {"suite": "reviewer-capacity-qualification", "reviewer_contract": reviewer.CONTRACT_VERSION,
            "reviewer_module_sha256": er._sha256_file(Path(reviewer.__file__).resolve()),
            "limits": limits, "calibration": CALIBRATION, "scales": list(scales), "runs": runs}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Reviewer capacity qualification sweep.")
    parser.add_argument("--out", default="", help="write the full sweep record to this path")
    parser.add_argument("--reviewer", default="v2731.8", choices=("v2731.8", "v2732.0"),
                        help="which reviewer to qualify")
    parser.add_argument("--scales", default="", help="comma-separated part counts")
    args = parser.parse_args()
    module = er
    scales = (19, 28, 30, 32, 34)
    if args.reviewer == "v2732.0":
        import experiment_review_hierarchical as hier

        module, scales = hier, (19, 27, 34, 48, 64)
    if args.scales:
        scales = tuple(int(x) for x in args.scales.split(","))
    record = sweep(scales, reviewer=module)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(record, indent=1), encoding="utf-8", newline="\n")
    for run in record["runs"]:
        m = run["measurements"]
        print(f"{run['band']:12s} {run['parts_target']:3d} parts  {m['status']:<12s} "
              f"final={m['final_budget']['chars']:6d}/{m['final_budget']['budget']} "
              f"({m['final_budget']['used']:6.1%})  coverage={m['part_coverage']['coverage']}  "
              f"missing={[x['kind'] for x in m['mechanical_verification']['missing']]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
