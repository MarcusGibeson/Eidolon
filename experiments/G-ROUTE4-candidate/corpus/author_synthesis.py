"""Author the 100 frozen G-ROUTE4 Hierarchical Semantic Synthesis slots.

This is deterministic corpus authoring only. It reads the frozen blueprint and the completed Extraction staging
artifact, verifies the frozen English-vocabulary provenance, replays Extraction's name draws, then continues the
same global invented-name stream. It contacts no model or adjudicator and creates no seal.

    python -B author_synthesis.py
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools"))
from english_vocabulary import english_vocabulary  # noqa: E402
from names import NameBank  # noqa: E402

BLUEPRINT = json.loads((ROOT / "experiments/G-ROUTE4-candidate/blueprint/BLUEPRINT.json").read_text(encoding="utf-8"))
TEMPLATE = BLUEPRINT["templates"]["hierarchical_semantic_synthesis"]["assembled_template"]
SLOTS = [s for s in BLUEPRINT["slots"] if s["task_class"] == "hierarchical_semantic_synthesis"]
EXTRACTION = json.loads((HERE / "staging/extraction.json").read_text(encoding="utf-8"))

DOMAINS = [
    "orchard", "foundry", "canal", "aviary", "brewery", "observatory", "greenhouse", "boathouse",
    "quarry", "bakery", "museum", "vineyard", "planetarium", "sawmill", "aquarium", "tramway",
    "archive", "dairy", "marina", "theatre", "nursery", "workshop", "apiary", "laundry", "gallery",
]
ASSETS = [
    "mist controller", "kiln damper", "lock beacon", "feed carousel", "mash chiller", "dome shutter",
    "vent actuator", "bilge alarm", "dust sampler", "proofing cabinet", "humidity logger", "press gauge",
    "projector interlock", "blade monitor", "salinity probe", "signal repeater", "shelf scanner",
    "pasteur timer", "tide display", "rigging sensor", "warming mat", "torque reader", "hive scale",
    "rinse meter", "light tracker",
]
SIGNALS = [
    "amber pulse", "pressure ripple", "blue marker", "feed interval", "cooling cycle", "azimuth reading",
    "airflow sample", "float position", "particle count", "heat plateau", "moisture trace", "clamp load",
    "door state", "vibration band", "salt reading", "track packet", "barcode sweep", "hold period",
    "waterline sample", "tension reading", "soil interval", "load curve", "colony reading", "wash phase",
    "exposure band",
]
EFFECTS = [
    "spraying evenly", "holding temperature", "showing clearance", "dispensing portions", "cooling batches",
    "tracking stars", "moving fresh air", "reporting seepage", "sampling fines", "holding dough",
    "recording humidity", "measuring force", "protecting the lens", "tracking blade speed", "reporting salinity",
    "relaying signals", "reading labels", "timing the hold", "showing depth", "measuring tension",
    "warming trays", "reporting torque", "weighing hives", "measuring rinse flow", "tracking illumination",
]
SECTORS = ["northern", "coastal", "upland", "riverside"]

CONCLUSIONS = {
    "SY1": ("cause_established", ["cause_established", "cause_unresolved", "insufficient_evidence"]),
    "SY2": ("cause_unresolved", ["cause_established", "cause_unresolved", "insufficient_evidence"]),
    "SY3": ("insufficient_evidence", ["cause_established", "cause_unresolved", "insufficient_evidence"]),
    "SY4": ("decision_reserved", ["decision_reserved", "decision_open", "insufficient_evidence"]),
    "SY5": ("constraint_breached", ["constraint_breached", "constraint_met", "insufficient_evidence"]),
    "SY6": ("behavior_by_design", ["behavior_by_design", "defect_found", "insufficient_evidence"]),
}

RULES = {
    "SY1": "Choose cause_established when a finding directly states the cause and nothing disputes it; choose cause_unresolved when counterevidence disputes a proposed cause; otherwise choose insufficient_evidence.",
    "SY2": "Choose cause_established when a finding directly states the cause and nothing disputes it; choose cause_unresolved when counterevidence disputes a proposed cause; otherwise choose insufficient_evidence.",
    "SY3": "Choose cause_established when a finding directly states the cause and nothing disputes it; choose cause_unresolved when counterevidence disputes a proposed cause; otherwise choose insufficient_evidence.",
    "SY4": "Choose decision_reserved when the evidence assigns the decision to a named role; choose decision_open when the evidence gives the current reviewer that authority; otherwise choose insufficient_evidence.",
    "SY5": "Choose constraint_breached when a finding exceeds or violates the stated constraint; choose constraint_met when the finding remains within it; otherwise choose insufficient_evidence.",
    "SY6": "Choose behavior_by_design when a policy or configuration accounts for the behavior; choose defect_found when the behavior breaks that policy or configuration; otherwise choose insufficient_evidence.",
}


def scenario(index):
    return (f"{SECTORS[index // 25]} {DOMAINS[index % 25]}", ASSETS[(index * 7) % 25], SIGNALS[(index * 11) % 25],
            EFFECTS[(index * 13) % 25])


def authored_observations(family, name, domain, asset, signal, effect, merge, large):
    if family == "SY1":
        texts = [
            f"At {name}, the {domain} {asset} stopped {effect} after the {signal} shifted.",
            f"The diagnostic trace for {name} directly attributes the interruption to a fractured relay in the {asset}.",
            f"The maintenance crew at {name} should inspect that relay before restoring the {domain} cycle.",
            f"The interruption delayed one scheduled {domain} check at {name}.",
            f"A controlled replay at {name} reproduced the interruption when the fractured relay opened.",
        ]
        roles = (["finding", "finding", "next_step", "impact", "verification"] if merge else
                 ["event", "causal_finding", "next_step", "impact", "verification"])
    elif family == "SY2":
        texts = [
            f"An initial review at {name} proposes that the {signal} caused the {asset} to stop {effect}.",
            f"A later trace from {name} shows the {signal} stayed normal during the same interruption.",
            f"The only confirmed fact is that the {domain} {asset} paused for one cycle at {name}.",
            f"No component-level test at {name} identifies a different cause.",
            f"The review team should isolate the {asset} inputs before assigning a cause at {name}.",
        ]
        roles = (["analysis", "analysis", "finding", "evidence_gap", "next_step"] if merge else
                 ["proposed_cause", "counterevidence", "finding", "evidence_gap", "next_step"])
    elif family == "SY3":
        texts = [
            f"One trial at {name} found the {domain} {asset} completed a single {signal} cycle.",
            f"That trial at {name} has no baseline or repeat measurement for comparison.",
            f"The analyst should collect repeated {asset} measurements before claiming a trend at {name}.",
            f"The trial covered only one operating shift in the {domain} area at {name}.",
            f"No historical series for the {signal} was supplied by {name}.",
        ]
        roles = (["finding", "finding", "next_step", "scope_limit", "comparison_gap"] if merge else
                 ["single_observation", "evidence_gap", "next_step", "scope_limit", "comparison_gap"])
    elif family == "SY4":
        texts = [
            f"The review at {name} asks whether the {domain} {asset} may return to service.",
            f"The operating charter for {name} assigns that decision only to the duty steward.",
            f"The handover note at {name} repeats that the duty steward must record the decision.",
            f"The current reviewer at {name} is listed as an observer, not the duty steward.",
            f"The evidence packet should be forwarded to the duty steward at {name} without deciding the request.",
        ]
        roles = (["request", "authority_boundary", "authority_boundary", "role_finding", "next_step"] if merge else
                 ["request", "authority_boundary", "handover_rule", "role_finding", "next_step"])
    elif family == "SY5":
        texts = [
            f"The {domain} {asset} at {name} recorded 84 units during the {signal} check.",
            f"The signed operating constraint for {name} limits that reading to 60 units.",
            f"The operator at {name} should hold the {asset} out of service pending inspection.",
            f"A second display at {name} also showed a reading above the 60-unit ceiling.",
            f"The exceedance affected the scheduled {domain} cycle at {name}.",
        ]
        roles = (["finding", "finding", "next_step", "corroboration", "impact"] if merge else
                 ["measurement", "constraint", "next_step", "corroboration", "impact"])
    else:
        texts = [
            f"At {name}, the {domain} {asset} delays {effect} whenever the {signal} enters hold mode.",
            f"The active configuration at {name} deliberately adds that delay during hold mode.",
            f"The operator at {name} should record the delay as configured behavior.",
            f"A configuration replay at {name} produced the same delay without an equipment fault.",
            f"The normal-mode cycle at {name} completed without the delay.",
        ]
        roles = (["finding", "finding", "next_step", "verification", "comparison"] if merge else
                 ["behavior", "configuration", "next_step", "verification", "comparison"])
    count = 5 if large else 3
    return texts[:count], roles[:count]


def anchors(text):
    words = re.findall(r"[A-Za-z0-9%]+", text)
    candidates = [w for w in words if len(w) >= 5]
    out = []
    for word in candidates:
        if word.casefold() not in {x.casefold() for x in out}:
            out.append(word)
        if len(out) == 2:
            break
    assert out
    return out


def replay_extraction_names(bank):
    replayed = []
    for row in EXTRACTION["design"]:
        for expected in row["invented_names"]:
            actual = bank.take()
            assert actual == expected, (row["fixture_id"], actual, expected)
            replayed.append(actual)
    return replayed


def build():
    english, provenance = english_vocabulary()
    assert provenance == EXTRACTION["english_vocabulary"], "frozen English vocabulary provenance changed"
    sys.path.insert(0, str(ROOT / "experiments/G-ROUTE4-candidate/blueprint"))
    import build_blueprint as B  # noqa: E402
    g3_entities, g3_lineages = B.g_route3_entity_inventory()
    bank = NameBank(english, set(g3_entities) | set(g3_lineages))
    replayed = replay_extraction_names(bank)

    body = TEMPLATE[len("{SUBJECT}"):]
    fixtures, gold, design = [], [], []
    synthesis_draws = 0
    for index, slot in enumerate(SLOTS, 1):
        fid, family = slot["fixture_id"], slot["family"]
        domain, asset, signal, effect = scenario(index - 1)
        merge = slot["features"]["mergeable_pair"] == "yes"
        large = slot["features"]["obs_band"] == "large"
        observation_count = 5 if large else 3
        names = [bank.take() for _ in range(observation_count)]
        first_ordinal = len(replayed) + synthesis_draws + 1
        synthesis_draws += observation_count
        name = names[0]
        texts, roles = authored_observations(family, name, domain, asset, signal, effect, merge, large)
        texts = [
            f"{names[i]} filed observation {index}-{i + 1}: {text} "
            f"{names[i]} links the {domain} record through {names[(i + 1) % observation_count]} to the {asset}; "
            f"{names[(i + 2) % observation_count]} compares the {signal} while {names[(i + 1) % observation_count]} "
            f"tracks {effect}. For {names[(i + 2) % observation_count]}, the {effect} evidence remains paired with "
            f"{names[(i + 1) % observation_count]}'s {signal} ledger rather than the {domain} summary."
            for i, text in enumerate(texts)
        ]
        if fid == "B4-SYNTH-R2-18":
            texts = [
                text + f" {names[i]} separately indexes a coastal discrepancy note beside "
                f"{names[(i + 2) % observation_count]}'s archived instrument sketch."
                for i, text in enumerate(texts)
            ]
        observation_ids = [f"O{index * 10 + offset}" for offset in range(1, len(texts) + 1)]
        observations = [{"id": oid, "role": role, "text": text}
                        for oid, role, text in zip(observation_ids, roles, texts)]
        conclusion, allowed = CONCLUSIONS[family]
        opening = f"Synthesize the {domain} {asset} review for {name}"
        prompt = TEMPLATE.replace("{SUBJECT}", opening)
        assert prompt == opening + body

        role_counts = Counter(roles)
        statements, consumed = [], set()
        for number, observation in enumerate(observations, 1):
            if observation["id"] in consumed:
                continue
            same = [row for row in observations if row["role"] == observation["role"]]
            group = same if len(same) == 2 else [observation]
            consumed.update(row["id"] for row in group)
            statements.append({
                "statement_id": f"S{index * 10 + number}", "role": observation["role"],
                "observation_ids": [row["id"] for row in group],
                "text": " ".join(row["text"] for row in group),
            })
        assert sorted(consumed) == sorted(observation_ids)
        assert sorted(n for n in role_counts.values() if n > 1) == ([2] if merge else [])
        required_terms = {row["id"]: anchors(row["text"]) for row in observations}
        expected = {"conclusion": conclusion, "required_terms": required_terms,
                    "roles": {row["id"]: row["role"] for row in observations}}
        reference = {"conclusion": conclusion, "statements": statements}
        rationale = {
            "SY1": "A finding directly states the cause and no observation disputes it.",
            "SY2": "Counterevidence disputes the proposed cause, so causality remains unresolved.",
            "SY3": "A single unreplicated observation cannot establish the claimed pattern.",
            "SY4": "The charter reserves the decision to the duty steward.",
            "SY5": "The observed reading exceeds the stated operating constraint.",
            "SY6": "The active configuration accounts for the observed behavior.",
        }[family]
        fixtures.append({
            "consequence_risk": slot["risk"], "fixture_id": fid,
            "input": {"allowed_conclusions": allowed, "conclusion_rule": RULES[family],
                      "observations": observations},
            "prompt": prompt, "task_class": "hierarchical_semantic_synthesis",
            "title": f"{domain.title()} {asset} review at {name}", "validator_profile": "synthesis.v1",
        })
        gold.append({"expected": expected, "fixture_id": fid, "rationale": rationale,
                     "reference_output": reference})
        design.append({
            "fixture_id": fid, "phase": slot["phase"], "role": slot["role"], "risk": slot["risk"],
            "family": family, "features": slot["features"], "invented_names": names,
            "identifiers": [], "global_name_ordinals": [first_ordinal, first_ordinal + observation_count - 1],
        })
    return {
        "schema_version": "g-route4.authoring-staging.v1",
        "task_class": "hierarchical_semantic_synthesis", "blueprint_commit": "1156d06",
        "status": "authored, not sealed, not adjudicated", "english_vocabulary": provenance,
        "name_sequence": {"extraction_names_replayed": len(replayed), "first_synthesis_ordinal": len(replayed) + 1,
                          "last_synthesis_ordinal": len(replayed) + synthesis_draws},
        "missing_slots": sorted({s["fixture_id"] for s in SLOTS} - {f["fixture_id"] for f in fixtures}),
        "fixtures": fixtures, "gold": gold, "design": design,
    }


if __name__ == "__main__":
    output = build()
    path = HERE / "staging/synthesis.json"
    path.write_text(json.dumps(output, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(output['fixtures'])} fixtures written; missing slots: {output['missing_slots']}")
    print("name sequence", output["name_sequence"])
