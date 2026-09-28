"""Author the 142 frozen G-ROUTE4 Ordinary Conversation slots.

Deterministic corpus authoring only, to the frozen blueprint at commit 1156d06. The script replays every name
already assigned to Extraction, Synthesis and Planning, then continues the same global stream. It contacts no model
or adjudicator and creates no seal.

Each fixture has exactly four options. The frozen gold position selects the sole candidate satisfying both computed
conditions. Exactly one wrong option satisfies the first condition but not the second; for depth 2 this is the
required correct-first-step/wrong-second-step near miss.

    python -B author_conversation.py
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools"))
from english_vocabulary import english_vocabulary  # noqa: E402
from names import NameBank  # noqa: E402

BLUEPRINT = json.loads((ROOT / "experiments/G-ROUTE4-candidate/blueprint/BLUEPRINT.json").read_text(encoding="utf-8"))
TEMPLATE = BLUEPRINT["templates"]["ordinary_conversation"]["assembled_template"]
SLOTS = [s for s in BLUEPRINT["slots"] if s["task_class"] == "ordinary_conversation"]
PRIOR = [json.loads((HERE / f"staging/{name}.json").read_text(encoding="utf-8"))
         for name in ("extraction", "synthesis", "planning")]

DOMAINS = [
    "allotment", "bell tower", "canal lock", "dye house", "estuary lab", "flour mill", "glass studio",
    "harbour shed", "island depot", "joinery loft", "kitchen garden", "lantern room", "map archive",
    "net house", "orchid room", "pottery yard", "quayside hall", "rail museum", "seed library",
    "tram depot", "upland lodge", "volunteer hub", "weaving room",
]
ASSETS = [
    "air sampler", "batch trolley", "chime motor", "drain pump", "exhibit cradle", "fermenting rack",
    "gate sensor", "humidity case", "inspection cart", "junction panel", "kiln shelf", "label printer",
    "mooring gauge", "nutrient tray", "oil cabinet", "parcel bench", "quality board", "rinse station",
    "signal mast", "tool locker", "ultraviolet meter", "visitor counter", "wash cabinet", "yarn stand",
    "zone thermostat", "archive scanner", "brew kettle", "cooling fan", "display plinth",
]
ACTIVITIES = [
    "spring survey", "evening handover", "weekly calibration", "stock rotation", "visitor setup",
    "sample transfer", "weather check", "maintenance round", "intake review", "label audit",
    "energy reading", "dispatch check", "storage review", "cleaning cycle", "opening inspection",
    "packing run", "quality pass", "route check", "safety briefing", "tool count", "usage review",
    "volunteer rota", "water test", "year-end count", "access review", "batch closeout", "courier window",
    "display reset", "equipment survey", "filter service", "garden round",
]
VERBS = ["Choose", "Identify", "Select", "Name", "Report", "Find", "State", "Determine"]
RISK_CONTEXT = {
    "R1": "The result concerns a reversible household or hobby choice",
    "R2": "The result concerns a reversible booking, order, or office record",
    "R3": "The result concerns a privacy, access, or compliance record",
    "R4": "The result is evidence-only for a safety or irreversible-operation record",
}
INSTRUCTIONS = {
    ("CV1", 1): "Choose the row whose two supplied condition flags are both true.",
    ("CV1", 2): "Choose the row whose base meets the minimum and whose adjusted total stays within the maximum.",
    ("CV2", 1): "Add each duration to its start; the arrival must equal the target and the duration must stay within the cap.",
    ("CV2", 2): "Add the first leg to reach the checkpoint, then add the second leg to reach the target.",
    ("CV3", 1): "Convert amount by factor; the result must equal the target while the source amount stays within its cap.",
    ("CV3", 2): "Convert amount by factor, then subtract reserve; both the converted and net targets must match.",
    ("CV4", 1): "Count values at or above the threshold and values below it; both counts must match their targets.",
    ("CV4", 2): "Count values at or above the threshold, then sum those values; both targets must match.",
    ("CV5", 1): "Compute each percentage; it must reach the threshold and its sample size must reach the minimum.",
    ("CV5", 2): "Compute the raw percentage, then subtract the stated adjustment; both thresholds must hold.",
    ("CV6", 1): "Apply the general rule and then its exception; choose the generally allowed row not blocked by the exception.",
    ("CV6", 2): "Apply the general rule with priority first, then the stated exception; both stages must allow the row.",
}


def arrange(gold, near, far_one, far_two, gold_position):
    rows = [None, None, None, None]
    gold_index = gold_position - 1
    near_index = gold_position % 4
    rows[gold_index] = gold
    rows[near_index] = near
    remaining = iter((far_one, far_two))
    for i in range(4):
        if rows[i] is None:
            rows[i] = next(remaining)
    return rows, near_index


def case_for(family, depth, number, gold_position):
    """Return input fields, ordered candidate rows, near-miss index, and a concise computation description."""
    if family == "CV1" and depth == 1:
        rows = [
            {"condition_one": True, "condition_two": True},
            {"condition_one": True, "condition_two": False},
            {"condition_one": False, "condition_two": False},
            {"condition_one": False, "condition_two": False},
        ]
        extra = {}
    elif family == "CV1":
        minimum, maximum = 30 + number, 38 + number
        rows = [
            {"adjustment": 3, "base": minimum + 2},
            {"adjustment": 9, "base": minimum + 2},
            {"adjustment": 12, "base": minimum - 2},
            {"adjustment": 13, "base": minimum - 3},
        ]
        extra = {"maximum": maximum, "minimum": minimum}
    elif family == "CV2" and depth == 1:
        target, cap = 600 + number, 25 + number % 7
        rows = [
            {"duration": cap - 2, "start": target - (cap - 2)},
            {"duration": cap + 2, "start": target - (cap + 2)},
            {"duration": cap + 3, "start": target - (cap + 3) - 5},
            {"duration": cap + 4, "start": target - (cap + 4) + 5},
        ]
        extra = {"duration_cap": cap, "target_minute": target}
    elif family == "CV2":
        start = 420 + number % 100
        first = 20 + number % 5
        second = 30 + number % 7
        checkpoint, target = start + first, start + first + second
        rows = [
            {"first_leg": first, "second_leg": second, "start": start},
            {"first_leg": first, "second_leg": second + 5, "start": start},
            {"first_leg": first - 5, "second_leg": second + 10, "start": start},
            {"first_leg": first + 5, "second_leg": second + 5, "start": start},
        ]
        extra = {"checkpoint_minute": checkpoint, "target_minute": target}
    elif family == "CV3" and depth == 1:
        target = 120 + 6 * number
        cap = target // 4
        rows = [
            {"amount": target // 6, "factor": 6},
            {"amount": target // 3, "factor": 3},
            {"amount": target // 3 + 1, "factor": 3},
            {"amount": target // 3 + 2, "factor": 3},
        ]
        extra = {"source_cap": cap, "target_converted": target}
    elif family == "CV3":
        target = 180 + 6 * number
        reserve = 10 + number % 9
        rows = [
            {"amount": target // 6, "factor": 6, "reserve": reserve},
            {"amount": target // 3, "factor": 3, "reserve": reserve + 2},
            {"amount": target // 3 + 1, "factor": 3, "reserve": reserve + 4},
            {"amount": target // 6 + 1, "factor": 6, "reserve": reserve + 5},
        ]
        extra = {"target_converted": target, "target_net": target - reserve}
    elif family == "CV4" and depth == 1:
        threshold = 40 + number
        rows = [
            {"values": [threshold + 1, threshold + 2, threshold - 1]},
            {"values": [threshold + 1, threshold + 2, threshold - 1, threshold - 2]},
            {"values": [threshold + 1, threshold - 1, threshold - 2]},
            {"values": [threshold + 1, threshold + 2, threshold + 3, threshold - 1, threshold - 2]},
        ]
        extra = {"target_count": 2, "target_secondary": 1, "threshold": threshold}
    elif family == "CV4":
        threshold = 40 + number
        rows = [
            {"values": [threshold + 1, threshold + 3, threshold - 1]},
            {"values": [threshold + 2, threshold + 3, threshold - 1]},
            {"values": [threshold + 1, threshold - 1, threshold - 2]},
            {"values": [threshold + 1, threshold + 2, threshold + 3, threshold - 1]},
        ]
        extra = {"target_count": 2, "target_secondary": 2 * threshold + 4, "threshold": threshold}
    elif family == "CV5" and depth == 1:
        threshold, minimum = 60 + number % 20, 80 + number
        rows = [
            {"denominator": 100, "numerator": threshold + 5, "sample_size": minimum + 10},
            {"denominator": 100, "numerator": threshold + 4, "sample_size": minimum - 10},
            {"denominator": 100, "numerator": threshold - 5, "sample_size": minimum - 12},
            {"denominator": 100, "numerator": threshold - 8, "sample_size": minimum - 14},
        ]
        extra = {"min_sample": minimum, "threshold": threshold}
    elif family == "CV5":
        raw = 60 + number % 10
        adjustment, final = 10, raw - 5
        rows = [
            {"denominator": 100, "numerator": raw + 10},
            {"denominator": 100, "numerator": raw + 2},
            {"denominator": 100, "numerator": raw - 5},
            {"denominator": 100, "numerator": raw - 8},
        ]
        extra = {"adjustment": adjustment, "final_threshold": final, "raw_threshold": raw}
    elif family == "CV6" and depth == 1:
        rows = [
            {"exception_applies": False, "general_allowed": True, "priority": 4},
            {"exception_applies": True, "general_allowed": True, "priority": 5},
            {"exception_applies": True, "general_allowed": False, "priority": 2},
            {"exception_applies": True, "general_allowed": False, "priority": 1},
        ]
        extra = {}
    else:
        required = 3 + number % 3
        rows = [
            {"exception_applies": False, "general_allowed": True, "priority": required + 1},
            {"exception_applies": True, "general_allowed": True, "priority": required + 1},
            {"exception_applies": True, "general_allowed": False, "priority": required - 1},
            {"exception_applies": True, "general_allowed": False, "priority": required - 2},
        ]
        extra = {"required_priority": required}
    ordered, near_index = arrange(*rows, gold_position)
    return extra, ordered, near_index


def replay_names(bank):
    replayed = []
    for staged in PRIOR:
        for row in staged["design"]:
            for expected in row["invented_names"]:
                actual = bank.take()
                assert actual == expected, (row["fixture_id"], actual, expected)
                replayed.append(actual)
    return replayed


def build():
    english, provenance = english_vocabulary()
    assert all(provenance == staged["english_vocabulary"] for staged in PRIOR)
    sys.path.insert(0, str(ROOT / "experiments/G-ROUTE4-candidate/blueprint"))
    import build_blueprint as B  # noqa: E402
    g3_entities, g3_lineages = B.g_route3_entity_inventory()
    bank = NameBank(english, set(g3_entities) | set(g3_lineages))
    replayed = replay_names(bank)
    assert PRIOR[-1]["name_sequence"]["last_planning_ordinal"] == len(replayed)

    body = TEMPLATE[len("{SUBJECT}"):]
    fixtures, gold, design = [], [], []
    drawn = 0
    for number, slot in enumerate(SLOTS, 1):
        fid, family = slot["fixture_id"], slot["family"]
        depth, position = slot["features"]["depth"], slot["features"]["gold_position"]
        names = [bank.take() for _ in range(4)]
        first_ordinal = len(replayed) + drawn + 1
        drawn += 4
        extra, candidates, near_index = case_for(family, depth, number, position)
        answer, near = names[position - 1], names[near_index]
        domain = DOMAINS[(number - 1) % len(DOMAINS)]
        asset = ASSETS[((number - 1) * 7) % len(ASSETS)]
        activity = ACTIVITIES[((number - 1) * 11) % len(ACTIVITIES)]
        opening = f"{VERBS[(number - 1) % len(VERBS)]} the listed candidate for the {domain} {asset} {activity} check"
        prompt = TEMPLATE.replace("{SUBJECT}", opening)
        assert prompt == opening + body
        message = (
            f"During the {activity} at the {domain}, candidates {names[0]}, {names[1]}, {names[2]}, and {names[3]} "
            f"match answer_options and candidate rows in order. {INSTRUCTIONS[(family, depth)]} "
            f"{RISK_CONTEXT[slot['risk']]}; this is record {number} for the {asset}. "
            f"{names[0]} pairs the {domain} notes with {names[1]}'s {activity} ledger, while {names[2]} checks the "
            f"{asset} figures under {names[3]}'s index. {names[3]} routes the first row through {names[0]}; "
            f"{names[1]} binds the second row to {names[2]}'s numbered worksheet. For this record, {names[2]} "
            f"keeps the third row beside {names[0]}'s local summary, and {names[3]} keeps the fourth beside "
            f"{names[1]}'s separate trace. {names[0]} tags the {activity} evidence for {names[2]}; {names[1]} "
            f"places the {domain} snapshot beside {names[3]}'s {asset} memo. {names[2]} traces record {number} "
            f"back through {names[0]}'s worksheet while {names[3]} audits {names[1]}'s row sequence. These links "
            "identify provenance only; calculate from candidate rows."
        )
        if fid == "B4-CONV-R3-X04":
            message += (f" {names[3]} also files a separate quayside comparison sheet under {names[0]}'s "
                        f"handwritten index; {names[2]} reconciles its margin marks with {names[1]}'s isolated "
                        "counter log before the candidate calculation.")
        inp = {"answer_options": names, "candidates": candidates, "message": message, **extra}
        rationale = (f"{answer} is the only option satisfying both computed conditions. {near} is the sole near "
                     "miss: it satisfies the first condition but fails the second.")
        reference = f"Answer: {answer}\nActions taken: none\n{rationale}"
        fixtures.append({
            "consequence_risk": slot["risk"], "fixture_id": fid, "input": inp, "prompt": prompt,
            "task_class": "ordinary_conversation", "title": f"{domain.title()} {asset} candidate review {number}",
            "validator_profile": "conversation.v1",
        })
        gold.append({"expected": {"answer": answer, "max_characters": 600}, "fixture_id": fid,
                     "rationale": rationale, "reference_output": reference})
        design.append({
            "fixture_id": fid, "phase": slot["phase"], "role": slot["role"], "risk": slot["risk"],
            "family": family, "features": slot["features"], "invented_names": names, "identifiers": [],
            "global_name_ordinals": [first_ordinal, first_ordinal + 3], "near_miss_option": near,
        })
    return {
        "schema_version": "g-route4.authoring-staging.v1", "task_class": "ordinary_conversation",
        "blueprint_commit": "1156d06", "status": "authored, not sealed, not adjudicated",
        "english_vocabulary": provenance,
        "name_sequence": {"names_replayed": len(replayed), "first_conversation_ordinal": len(replayed) + 1,
                          "last_conversation_ordinal": len(replayed) + drawn},
        "missing_slots": sorted({s["fixture_id"] for s in SLOTS} - {f["fixture_id"] for f in fixtures}),
        "fixtures": fixtures, "gold": gold, "design": design,
    }


if __name__ == "__main__":
    output = build()
    path = HERE / "staging/conversation.json"
    path.write_text(json.dumps(output, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(output['fixtures'])} fixtures written; missing slots: {output['missing_slots']}")
    print("name sequence", output["name_sequence"])
