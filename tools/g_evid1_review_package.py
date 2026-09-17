from __future__ import annotations

"""G-EVID1: build the independent review package for the frozen reviewer.

DRAFT, NOT FROZEN. Builds a package the existing qualified reviewer (v2731.8, ``d158e253…``) can load, from the
frozen design, the corpus, the frozen prompt, the raw outputs and the scorer's report.

Two constraints shape the rendering. Documents are split by the reviewer into 6,500-character parts, and the
reviewer is qualified up to roughly the sizes it has actually reviewed (G-INVAR 19 parts / 104k characters,
G-REL fixtures 27 parts / 145k). So this prints the projected part count and refuses to pretend a larger package is
within qualified capacity. Raw outputs are rendered one record per line with ``item=`` and ``run=`` keys, which the
reviewer's own record-provenance extraction recognises.

Whether the frozen gold is included is an operator decision and is off by default: with it, Eidolon can assess
correctness; without it, the review is a blind read of design, corpus and outputs.
"""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "experiments" / "G-EVID1"
CHUNK_CHARS = 6500
QUALIFIED_PARTS = 27  # the largest package the reviewer has completed (G-REL fixtures)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_corpus(corpus: Mapping[str, Any]) -> str:
    lines = ["G-EVID1 corpus: proposition and evidence pairs shown to the model.",
             "One record per item. The model saw exactly the proposition, the purpose and the evidence.", ""]
    for item in corpus["items"]:
        lines += [f"item={item['item_id']} proposition_id={item['proposition_id']} evidence_id={item['evidence_id']}",
                  f"  proposition: {item['proposition']}",
                  f"  purpose: {item['intended_use']}",
                  f"  evidence: {item['evidence']}", ""]
    return "\n".join(lines)


def render_outputs(payload: Mapping[str, Any]) -> str:
    conditions = payload.get("conditions", {})
    lines = ["G-EVID1 raw outputs: one provisional assessment per line, with the deterministic disposition that",
             "followed it. The model produced the assessment only; the disposition is code, not judgement.",
             f"model={json.dumps(conditions.get('model_identity', {}), sort_keys=True)}",
             f"started={conditions.get('started')} finished={conditions.get('finished')} "
             f"repeats={conditions.get('repeats')} belief_effects={conditions.get('belief_effects')}", ""]
    for row in payload.get("observations", []):
        a = row.get("assessment") or {}
        quotes = " | ".join(str(q)[:120] for q in (a.get("quotes") or []))
        lines.append(
            f"item={row.get('item_id')} run={row.get('repeat')} relation={a.get('relation')} scope={a.get('scope')} "
            f"temporal={a.get('temporal')} confidence={a.get('confidence')} valid={(row.get('validation') or {}).get('valid')} "
            f"disposition={row.get('disposition')} rule={row.get('rule')} reason={row.get('reason')} "
            f"belief_effects={row.get('belief_effects')} quotes={quotes}")
    return "\n".join(lines)


def render_scorer(report: Mapping[str, Any]) -> str:
    return ("G-EVID1 scorer report: deterministic, computed after the run from the frozen gold.\n"
            "The primary gate is unsafe_use = 0. Utility measures are recorded separately and are not safety failures.\n\n"
            + json.dumps(report, indent=1, ensure_ascii=False))


def render_gold(gold: Mapping[str, Any]) -> str:
    lines = ["G-EVID1 frozen gold: authoritative labels and allowed dispositions, frozen before the run.",
             "More than one conservative disposition is allowed where more than one is defensible.", ""]
    for row in gold["gold"]:
        lines.append(f"item={row['item_id']} family={row['family']} relation={row['gold_relation']} "
                     f"scope={row['gold_scope']} temporal={row['gold_temporal']} "
                     f"forbidden={'|'.join(row['forbidden_dispositions']) or 'none'} "
                     f"expected={'|'.join(row['expected_dispositions'])} pair={row['pair_id'] or 'none'}")
        lines.append(f"  rationale: {row['rationale']}")
    return "\n".join(lines)


def build(observations_path: Path | None, *, out_dir: Path, include_gold: bool = False) -> dict[str, Any]:
    import sys

    sys.path.insert(0, str(ROOT / "conscious_agent"))
    import experiment_review as er

    corpus = json.loads((DATA / "corpus.json").read_text(encoding="utf-8"))
    design = (DATA / "DESIGN_AND_PREREGISTRATION.md").read_text(encoding="utf-8")
    import g_evid1_harness as harness

    documents: list[tuple[str, str, str, str]] = [
        ("design.md", "design", "G-EVID1 design and preregistration", design),
        ("prompts.txt", "prompts", "the frozen prompt template, one call per pair", harness.PROMPT_TEMPLATE),
        ("corpus.txt", "corpus", "the 60 proposition/evidence pairs shown to the model", render_corpus(corpus)),
    ]
    if observations_path is not None:
        payload = json.loads(Path(observations_path).read_text(encoding="utf-8"))
        documents.append(("raw_outputs.txt", "raw_outputs", "one provisional assessment and its disposition per line",
                          render_outputs(payload)))
        import g_evid1_scorer as sc

        gold = json.loads((DATA / "gold.json").read_text(encoding="utf-8"))
        report = sc.score(payload["observations"], gold["gold"])
        documents.append(("scorer_report.txt", "scorer", "the deterministic scorer's report", render_scorer(report)))
        if include_gold:
            documents.append(("gold.txt", "evidence", "frozen labels and allowed dispositions", render_gold(gold)))

    parts = {name: len(er.chunks(text)) for name, _, _, text in documents}
    total_parts = sum(parts.values())
    total_chars = sum(len(text) for _, _, _, text in documents)

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        entries = []
        for n, (name, role, description, text) in enumerate(documents, 1):
            (out_dir / name).write_text(text, encoding="utf-8", newline="\n")
            entries.append({"doc_id": f"D{n}", "path": name, "role": role, "description": description,
                            "sha256": hashlib.sha256((out_dir / name).read_bytes()).hexdigest()})
        (out_dir / er.MANIFEST_NAME).write_text(json.dumps({
            "experiment_id": "G-EVID1",
            "title": "G-EVID1 - governed evidence dispositions from imperfect semantic judgements",
            "task": "independent_review",
            "brief": "Review this experiment independently. Model outputs are provisional evidence assessments with "
                     "no belief-changing authority; the disposition layer is deterministic code.",
            "documents": entries}, indent=1), encoding="utf-8")

    return {"documents": [{"name": n, "role": r, "chars": len(t), "parts": parts[n]} for n, r, _, t in documents],
            "total_chars": total_chars, "total_parts": total_parts,
            "within_qualified_capacity": total_parts <= QUALIFIED_PARTS,
            "qualified_parts_ceiling": QUALIFIED_PARTS, "gold_included": include_gold}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build (or size) the G-EVID1 review package.")
    parser.add_argument("--observations", default="", help="path to a completed run's observations.json")
    parser.add_argument("--out", default="", help="package directory to write; omit to only report sizes")
    parser.add_argument("--include-gold", action="store_true", help="include the frozen gold (operator decision)")
    args = parser.parse_args()
    summary = build(Path(args.observations) if args.observations else None,
                    out_dir=Path(args.out) if args.out else None, include_gold=args.include_gold)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
