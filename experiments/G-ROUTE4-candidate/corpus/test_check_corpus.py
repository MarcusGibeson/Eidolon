"""Proves each checker rule fires: one planted defect per rule, on a copy of the staged corpus.

    python -B test_check_corpus.py staging/extraction.json
"""

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_corpus as C  # noqa: E402


def by_id(staged, fid):
    f = next(x for x in staged["fixtures"] if x["fixture_id"] == fid)
    g = next(x for x in staged["gold"] if x["fixture_id"] == fid)
    d = next(x for x in staged["design"] if x["fixture_id"] == fid)
    return f, g, d


def mutate_text(s, fid, old, new):
    f, g, d = by_id(s, fid)
    assert old in f["input"]["text"], (fid, old)
    f["input"]["text"] = f["input"]["text"].replace(old, new)


def m_shared_entity(s):
    a = by_id(s, "B4-EXTR-R1-02")[2]["invented_names"][0]
    f, g, d = by_id(s, "B4-EXTR-R2-03")
    f["input"]["text"] += f" The claim was countersigned by {a}."
    d["invented_names"].append(a)


def m_undeclared(s):
    mutate_text(s, "B4-EXTR-R1-11", "delivered to a locker", "delivered to a locker by Gorbutrex")


def m_english_name(s):
    # an English word can only enter as a name by leaving the committed, dictionary-screened stream
    f, g, d = by_id(s, "B4-EXTR-R1-01")
    old = d["invented_names"][0]
    f["input"]["text"] = f["input"]["text"].replace(old, "Banana")
    d["invented_names"][0] = "Banana"


def m_jaccard(s):
    src = by_id(s, "B4-EXTR-R2-16")[0]
    f, g, d = by_id(s, "B4-EXTR-R2-17")
    f["input"]["text"] = src["input"]["text"]
    f["title"] = src["title"]


def m_o6_g3(s):
    f, g, d = by_id(s, "B4-EXTR-R1-01")
    mutate_text(s, "B4-EXTR-R1-01", "river moss", "fern")
    g["expected"]["glaze"] = g["reference_output"]["glaze"] = "fern"


def m_o6_g4(s):
    a = by_id(s, "B4-EXTR-R1-03")[1]["expected"]["played_on"]
    f, g, d = by_id(s, "B4-EXTR-R2-05")
    f["input"]["text"] = f["input"]["text"].replace("2047-03-19", a)
    g["expected"]["meeting_date"] = g["reference_output"]["meeting_date"] = a


def m_derived(s):
    f, g, d = by_id(s, "B4-EXTR-R2-05")
    f["prompt"] = f["prompt"].replace("Extract the room booking", "Extract the room booking. capacity is the seats")


def m_suffix(s):
    f, g, d = by_id(s, "B4-EXTR-R2-13")
    sch = f["input"]["schema"]
    f["input"]["schema"] = {("kg" if k == "cartons" else k): v for k, v in sch.items()}
    for x in (g["expected"], g["reference_output"]):
        x["kg"] = x.pop("cartons")
    f["input"]["schema"] = {k: f["input"]["schema"][k] for k in ["consignment", "kg", "gross_kg"]}


def m_integer_float(s):
    f, g, d = by_id(s, "A4-EXTR-R4-01")
    g["expected"]["total_load_kg"] = g["reference_output"]["total_load_kg"] = 2460.0


def m_period(s):
    f, g, d = by_id(s, "A4-EXTR-R1-04")
    f["prompt"] = f["prompt"].replace("above 40 ppm. Copy", "above 40 ppm.. Copy")


def m_absence_missing(s):
    f, g, d = by_id(s, "B4-EXTR-R1-15")
    f["prompt"] = f["prompt"].replace(". " + C.ABSENCE[:-1], "")


def m_types(s):
    f, g, d = by_id(s, "B4-EXTR-R1-07")
    f["input"]["schema"]["plot"] = "number"


def m_signature(s):
    # give a B′ R1 fixture exactly an A′ R1 signature: A4-EXTR-R1-03 is (integer, number, string; derived 2)
    f, g, d = by_id(s, "B4-EXTR-R1-01")          # (boolean, integer, string; derived 1)
    f["input"]["schema"]["same_day_pickup"] = "number"
    g["expected"]["same_day_pickup"] = g["reference_output"]["same_day_pickup"] = 0
    f["prompt"] = f["prompt"].replace("fired. Copy", "fired. same_day_pickup is zero. Copy")
    d["derived_keys"].append("same_day_pickup")


def m_n1(s):
    a = by_id(s, "B4-EXTR-R2-17")
    b = by_id(s, "B4-EXTR-R2-X01")
    b[0]["input"]["schema"] = copy.deepcopy(a[0]["input"]["schema"])
    b[1]["expected"] = copy.deepcopy(a[1]["expected"])
    b[1]["reference_output"] = copy.deepcopy(a[1]["expected"])


def m_gold_wrong(s):
    f, g, d = by_id(s, "B4-EXTR-R2-10")
    g["expected"]["decision"] = "pay"
    g["reference_output"]["decision"] = "hold"


def m_cap(s):
    for fid in ("B4-EXTR-R1-01", "B4-EXTR-R1-02", "B4-EXTR-R1-03", "B4-EXTR-R1-04", "B4-EXTR-R1-05",
                "B4-EXTR-R1-06", "B4-EXTR-R1-07"):
        by_id(s, fid)[2]["family"] = "EX1"


CASES = {
    m_shared_entity: "O3 shared named entity", m_undeclared: "not declared as invented",
    m_english_name: "not the committed stream slice", m_jaccard: "trigram Jaccard", m_o6_g3: "O6 shared value",
    m_o6_g4: "O6 shared value", m_derived: "derived measure", m_suffix: "is a suffix of key",
    m_integer_float: "integer field", m_period: "terminal period", m_absence_missing: "absence sentence count",
    m_types: "field types", m_signature: "fine signature repeated", m_n1: "N1 identical canonical gold",
    m_gold_wrong: "reference_output differs", m_cap: "design record differs from the slot",
}

if __name__ == "__main__":
    base = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    clean, _ = C.check([base])
    assert not clean, None if not clean else clean
    print("clean corpus: 0 problems")
    failed = 0
    for fn, expect in CASES.items():
        s = copy.deepcopy(base)
        fn(s)
        problems, _ = C.check([s])
        hit = [p for p in problems if expect in p]
        print(("FIRES " if hit else "MISSED"), fn.__name__, "->", hit[0] if hit else problems[:3])
        failed += not hit
    print(f"{len(CASES) - failed} of {len(CASES)} planted defects caught")
    sys.exit(1 if failed else 0)
