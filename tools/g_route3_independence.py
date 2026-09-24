from __future__ import annotations

"""Design-time independence audit between G-ROUTE3 Corpus A and Corpus B.

Reads both corpora and both gold files together, which is permissible only because it
runs before any model contact and is never imported by collection, routing or scoring.
"""

from collections import Counter, defaultdict
from itertools import product
import json
import re
import sys
from pathlib import Path
from typing import Any

from g_route3_contract import DATA, load_corpus, load_gold, load_json

CONTRACT_VERSION = "g-route3.independence-audit.v1"
MAX_CROSS_CORPUS_TRIGRAM_JACCARD = 0.20
BOILERPLATE_SHARE = 0.25
_WORD = re.compile(r"[a-z0-9][a-z0-9_.\-%:]*")
_ENTITY = re.compile(r"\b(?:[A-Z][a-z]+(?:[A-Z][a-z]+)*|[A-Z]{1,5}-?\d[\w.-]*)\b")
_COMMON = {"The", "A", "An", "Only", "Each", "Every", "No", "Do", "Use", "When", "If", "Plan", "Recommend",
           "Conclude", "Assess", "Synthesize", "Extract", "Repair", "Answer", "Respond", "Tell", "Give", "Offer",
           "Summarize", "Count", "Status", "Include", "Order", "Number", "Set", "List", "Choose", "Restate",
           "Merge", "Cite", "Return", "In", "Not", "Yes", "Our", "Mine", "We", "Your", "It", "This", "Its",
           "Advise", "Explain", "Report", "Decline", "Name", "Name", "Can", "Is", "Has", "Did", "Which", "What",
           "How", "Storage", "Policy", "Press", "Plans", "Weight", "Listed", "Office", "Fully", "Course", "Pause",
           "Delivery", "Backups", "All", "Heavy", "Good", "Applicants", "Edits", "Release", "Firmware", "Panel"}


# Profile-level rule vocabulary shared by design. It defines the task class being qualified,
# is identical wherever it is used, and is declared in the report rather than counted as content.
SHARED_RULE_KEYS = ("allowed_uncertainty_codes", "conclusion_rule", "allowed_conclusions")
# Tokens that come from disclosed profile-level rule text, not fixture content.
SHARED_RULE_TOKENS = {"PurePosixPath"}
_WEEKDAYS_MONTHS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "January",
                    "February", "March", "April", "May", "June", "July", "August", "September", "October",
                    "November", "December"}


def _content(fixture: dict[str, Any]) -> str:
    data = {k: v for k, v in dict(fixture["input"]).items() if k not in SHARED_RULE_KEYS}
    return fixture["title"] + " " + fixture["prompt"] + " " + json.dumps(data, ensure_ascii=False)


def _named_entities(text: str, lowercase_vocabulary: set[str]) -> set[str]:
    """Proper names and identifiers: mid-sentence capitalized words never used in lowercase,
    and alphanumeric identifiers longer than a structural id such as C1 or F2."""
    out = set()
    for match in re.finditer(r"(?<=[a-z,] )([A-Z][a-z]+(?:[A-Z][a-z]+)*)", text):
        word = match.group(1)
        if (word.lower() not in lowercase_vocabulary and word not in _WEEKDAYS_MONTHS and word not in _COMMON
                and word not in SHARED_RULE_TOKENS):
            out.add(word)
    for match in re.finditer(r"([A-Z]{1,5}-?\d[\w.-]*)", text):
        if not re.fullmatch(r"[A-Z]\d", match.group(1)):
            out.add(match.group(1))
    return out


def _trigrams(text: str) -> set[tuple[str, str, str]]:
    words = _WORD.findall(text.lower())
    return {tuple(words[i:i + 3]) for i in range(len(words) - 2)}


# Task classes whose construct is, by design, a single answer template. Their A and B fixtures are
# fresh instances of the same template with matched difficulty, and the claim is scoped accordingly.
SINGLE_TEMPLATE_TASK_CLASSES = {
    "reflective_planning": ("Every planning fixture has four included steps in a stated total order, one excluded "
                            "action and one holding uncertainty code. Planning is qualified as that construct."),
}


def _field_type(schema: Any) -> str:
    """Abstract schema types so relabelled enum values or date formats cannot hide a shared shape."""
    text = str(schema)
    if "|" in text:
        return f"enum{len(text.split('|'))}"
    if text in ("YYYY-MM-DD", "HH:MM"):
        return "date_or_time"
    return text


def structural_signature(fixture: dict[str, Any], expected: dict[str, Any]) -> Any:
    """Shape of the gold answer, independent of wording and entities. None when no shape is defined."""
    profile = fixture["validator_profile"]
    if profile == "research.v1":
        recommendations = fixture["input"]["allowed_recommendations"]
        return ("research",
                tuple(sorted((c["status"], len(c["citations"]), len(c["lineages"])) for c in expected["claims"])),
                recommendations.index(expected["recommendation"]), tuple(expected["uncertainties"]),
                len(fixture["input"]["sources"]), fixture["input"]["decision_rule"].split(" only if")[1][:40]
                if " only if" in fixture["input"]["decision_rule"] else "")
    if profile == "synthesis.v1":
        return ("synthesis", tuple(sorted(expected["roles"].values())), expected["conclusion"])
    if profile == "extraction.v1":
        derived = sum(f"{key} is " in fixture["prompt"] for key in fixture["input"]["schema"])
        return ("extraction", tuple(sorted(_field_type(v) for v in fixture["input"]["schema"].values())), derived)
    if profile == "planning.v1":
        return ("planning", len(expected["steps"]), len(fixture["input"]["allowed_actions"]),
                len(fixture["input"]["evidence"]), len(expected["uncertainties"]))
    return None


def coarse_signature(fixture: dict[str, Any], expected: dict[str, Any]) -> Any:
    """A deliberately coarse research shape (round 3): claim statuses, the recommendation's position, and why a
    claim is unresolved (conflict, scope or unaddressed), ignoring lineage counts.
    The fine signature also counts citations and lineages, so two fixtures posing the same problem could
    differ in a lineage count alone and pass."""
    if fixture["validator_profile"] != "research.v1":
        return None
    reason_codes = tuple(sorted(set(expected["uncertainties"]) - {"single_lineage_support"}))
    return ("research-coarse", tuple(sorted(c["status"] for c in expected["claims"])),
            fixture["input"]["allowed_recommendations"].index(expected["recommendation"]), reason_codes)


def audit() -> dict[str, Any]:
    corpora = {c: load_corpus(c)["fixtures"] for c in ("A", "B")}
    gold = {c: {g["fixture_id"]: g["expected"] for g in load_gold(c)["items"]} for c in ("A", "B")}
    design = {d["fixture_id"]: d for d in load_json(DATA / "fixture_design.json")["items"]}
    findings: list[str] = []

    by_task: dict[str, dict[str, list[dict]]] = defaultdict(lambda: {"A": [], "B": []})
    for corpus, rows in corpora.items():
        for row in rows:
            by_task[row["task_class"]][corpus].append(row)

    similarity = {}
    for task, parts in sorted(by_task.items()):
        grams = {row["fixture_id"]: _trigrams(_content(row)) for c in ("A", "B") for row in parts[c]}
        counts = Counter(g for gs in grams.values() for g in gs)
        boiler = {g for g, n in counts.items() if n >= BOILERPLATE_SHARE * len(grams)}
        pairs = []
        for a, b in product(parts["A"], parts["B"]):
            ga, gb = grams[a["fixture_id"]] - boiler, grams[b["fixture_id"]] - boiler
            j = len(ga & gb) / len(ga | gb) if ga | gb else 0.0
            pairs.append((round(j, 4), a["fixture_id"], b["fixture_id"]))
        pairs.sort(reverse=True)
        similarity[task] = {"max_trigram_jaccard": pairs[0][0], "max_pair": pairs[0][1:],
                            "mean_trigram_jaccard": round(sum(p[0] for p in pairs) / len(pairs), 4),
                            "boilerplate_trigrams_excluded": len(boiler)}
        if pairs[0][0] > MAX_CROSS_CORPUS_TRIGRAM_JACCARD:
            findings.append(f"trigram_overlap_above_bound:{task}:{pairs[0]}")

    lowercase_vocabulary = {w for rows in corpora.values() for row in rows
                            for w in re.findall(r"(?<![A-Za-z])[a-z]+", _content(row))}
    entities = {c: set() for c in ("A", "B")}
    for c, rows in corpora.items():
        for row in rows:
            entities[c] |= _named_entities(_content(row), lowercase_vocabulary)
    shared_entities = sorted(entities["A"] & entities["B"])
    if shared_entities:
        findings.append("shared_named_entities:" + ",".join(shared_entities))

    def answers(corpus: str, profile: str, extract) -> set[str]:
        out = set()
        for row in corpora[corpus]:
            if row["validator_profile"] == profile:
                out |= set(extract(row, gold[corpus][row["fixture_id"]]))
        return out

    shared_answers = {
        "planning_actions": sorted(answers("A", "planning.v1", lambda r, g: [s["action"] for s in g["steps"]])
                                   & answers("B", "planning.v1", lambda r, g: [s["action"] for s in g["steps"]])),
        "coding_function_names": sorted(
            answers("A", "coding.v1", lambda r, g: re.findall(r"def (\w+)", g["new"]))
            & answers("B", "coding.v1", lambda r, g: re.findall(r"def (\w+)", g["new"]))),
        "extraction_string_values": sorted(
            answers("A", "extraction.v1", lambda r, g: [v for v in g.values() if isinstance(v, str) and "-" not in v[:5]])
            & answers("B", "extraction.v1", lambda r, g: [v for v in g.values() if isinstance(v, str) and "-" not in v[:5]])),
        "research_source_lineages": sorted(
            answers("A", "research.v1", lambda r, g: [s["lineage"] for s in r["input"]["sources"]])
            & answers("B", "research.v1", lambda r, g: [s["lineage"] for s in r["input"]["sources"]])),
    }
    for key, values in shared_answers.items():
        if values:
            findings.append(f"shared_{key}:" + ",".join(values))

    cells: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(lambda: {"A": set(), "B": set()})
    for fid, d in design.items():
        cells[(d["task_class"], d["risk_class"])][d["corpus"]].add(d["pattern"])
    shared_patterns = {f"{t}|{r}": sorted(v["A"] & v["B"]) for (t, r), v in cells.items() if v["A"] & v["B"]}
    if shared_patterns:
        findings.append(f"cell_patterns_shared:{shared_patterns}")
    structural_pairs = []
    exempt_pairs = []
    by_cell: dict[tuple[str, str], dict[str, list[Any]]] = defaultdict(lambda: {"A": [], "B": []})
    for corpus, rows in corpora.items():
        for row in rows:
            for signature in (structural_signature(row, gold[corpus][row["fixture_id"]]),
                              coarse_signature(row, gold[corpus][row["fixture_id"]])):
                if signature is not None:
                    by_cell[(row["task_class"], row["consequence_risk"])][corpus].append((row["fixture_id"], signature))
    for (task, risk), parts in sorted(by_cell.items()):
        for (a_id, a_sig), (b_id, b_sig) in product(parts["A"], parts["B"]):
            if a_sig == b_sig:
                if task in SINGLE_TEMPLATE_TASK_CLASSES:
                    exempt_pairs.append([a_id, b_id])
                elif [a_id, b_id] not in structural_pairs:
                    structural_pairs.append([a_id, b_id])
    if structural_pairs:
        findings.append(f"same_gold_structure_within_cell:{structural_pairs}")
    # Informational: the same answer shape in A and B in DIFFERENT cells. Qualification and validation are
    # per cell, so this is not a finding, but it is reported so the reader can see where shapes recur.
    cross_cell = []
    flat = {corpus: [(cell, fid, sig) for cell, parts in by_cell.items() for fid, sig in parts[corpus]]
            for corpus in ("A", "B")}
    for (a_cell, a_id, a_sig), (b_cell, b_id, b_sig) in product(flat["A"], flat["B"]):
        if a_cell != b_cell and a_sig == b_sig and [a_id, b_id] not in cross_cell:
            cross_cell.append([a_id, b_id])
    # Conversation answer positions: within every cell the A and B fixtures must place the gold option at the
    # same positions, so option position cannot favour one corpus (round-4 review).
    position_mismatches = []
    positions: dict[tuple[str, str], dict[str, list[tuple[int, int]]]] = defaultdict(lambda: {"A": [], "B": []})
    for corpus, rows in corpora.items():
        for row in rows:
            if row["validator_profile"] == "conversation.v1":
                options = row["input"]["answer_options"]
                positions[(row["task_class"], row["consequence_risk"])][corpus].append(
                    (options.index(gold[corpus][row["fixture_id"]]["answer"]), len(options)))
    for cell, parts in sorted(positions.items()):
        if sorted(p for p, _ in parts["A"]) != sorted(p for p, _ in parts["B"]):
            position_mismatches.append(f"{cell[0]}|{cell[1]}:A{sorted(parts['A'])}:B{sorted(parts['B'])}")
    if position_mismatches:
        findings.append(f"conversation_answer_position_imbalance:{position_mismatches}")
    domains = {c: Counter(design[row["fixture_id"]]["domain"] for row in rows) for c, rows in corpora.items()}
    shared_domains = sorted(set(domains["A"]) & set(domains["B"]))

    return {
        "contract_version": CONTRACT_VERSION,
        "valid": not findings, "findings": findings,
        "bounds": {"max_cross_corpus_trigram_jaccard": MAX_CROSS_CORPUS_TRIGRAM_JACCARD,
                   "boilerplate_share": BOILERPLATE_SHARE},
        "trigram_similarity_by_task_class": similarity,
        "shared_named_entities": shared_entities,
        "shared_answers": shared_answers,
        "cell_patterns_shared": shared_patterns,
        "cells_checked": len(cells),
        "same_gold_structure_within_cell": structural_pairs,
        "conversation_answer_position_mismatches": position_mismatches,
        "same_gold_structure_across_cells_informational": sorted(cross_cell),
        "single_template_task_classes": SINGLE_TEMPLATE_TASK_CLASSES,
        "single_template_pairs_declared": exempt_pairs,
        "structural_check_scope": ("research, synthesis, extraction and planning compare the shape of the gold "
                                   "answer; conversation and coding have no structural signature and rely on the "
                                   "external review of reasoning patterns"),
        "shared_domains_across_different_cells": shared_domains,
        "shared_rule_keys_excluded_from_content": list(SHARED_RULE_KEYS),
        "shared_rule_tokens_excluded": sorted(SHARED_RULE_TOKENS),
        "note": ("Task class, risk class and the profile-level vocabularies (research status and uncertainty codes, "
                 "synthesis conclusion codes, planning exclusion prefixes) are shared by design; they define the "
                 "classes being qualified and are not fixture content."),
    }


def main() -> int:
    report = audit()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                                     encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in report.items() if k != "trigram_similarity_by_task_class"}, indent=2, sort_keys=True))
    for task, row in report["trigram_similarity_by_task_class"].items():
        print(f"  {task:34s} max {row['max_trigram_jaccard']:.3f} {row['max_pair']}  mean {row['mean_trigram_jaccard']:.3f}")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
