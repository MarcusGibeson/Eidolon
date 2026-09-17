from __future__ import annotations

"""G-EVID1: build the candidate corpus and the frozen gold specification.

DRAFT, NOT FROZEN. Writes ``experiments/G-EVID1/corpus.json`` (what the model is shown) and
``experiments/G-EVID1/gold.json`` (labels and dispositions, never shown to the model), then prints their digests.

Every subject is fictional on purpose. A model asked whether evidence supports a proposition about a real system can
answer from prior knowledge instead of from the passage; about the Meridian gateway or the Arden index it cannot, so
the judgement has to come from the evidence in front of it.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments" / "G-EVID1"

USE, INVESTIGATE, ABSTAIN = "use", "investigate", "abstain"

# --- shared evidence passages, reused so that families form minimal pairs -------------------------------------------
E = {
    "gateway": "Operations note 14: the Meridian gateway returns HTTP 413 for any request body above 8 MB. "
               "The limit has been in force since the gateway was first deployed.",
    "recon": "The Northwind runbook states that batch reconciliation executes every night at 02:15 local time.",
    "kestrel": "Kestrel firmware notes: all temperature values emitted by the sensor are in degrees Celsius.",
    "approver": "Policy 7.2: any order exceeding 500 units must be approved by a second authorised approver "
                "before dispatch.",
    "arden": "Quarterly bulletin: the Arden index stood at 42 for the most recent published quarter.",
    "tickets": "Helpdesk configuration: tickets with no activity for 30 days are closed automatically by the "
               "nightly job.",
    "halden": "Design note: Halden pipeline checkpoints are written to object storage rather than the local disk.",
    "bramley": "Migration status: of the four Bramley regions, two now run the new schema and two remain on the "
               "old one.",
}

ITEMS: list[dict] = []
GOLD: list[dict] = []


def add(item_id, family, proposition, intended_use, evidence, *, relation, scope="match", temporal="compatible",
        forbidden=(), expected=(), rationale="", pair_id="", differs=""):
    ITEMS.append({"item_id": item_id, "proposition_id": f"P{item_id[1:]}", "evidence_id": f"E{item_id[1:]}",
                  "proposition": proposition, "intended_use": intended_use, "evidence": evidence})
    GOLD.append({"item_id": item_id, "family": family, "gold_relation": relation, "gold_scope": scope,
                 "gold_temporal": temporal, "forbidden_dispositions": sorted(forbidden),
                 "expected_dispositions": sorted(expected), "rationale": rationale,
                 "pair_id": pair_id, "differs": differs})


SUPPORT_USE = "decide whether this evidence may be cited as support for the proposition"

# --- A. clear direct support (8) ------------------------------------------------------------------------------------
support = [
    ("I01", "The Meridian gateway rejects requests larger than 8 MB.", E["gateway"], "A1"),
    ("I02", "Batch reconciliation at Northwind runs nightly.", E["recon"], "A2"),
    ("I03", "The Kestrel sensor reports temperature in Celsius.", E["kestrel"], "A3"),
    ("I04", "Orders over 500 units require a second approver.", E["approver"], "A4"),
    ("I05", "The Arden index was 42 in the most recent published quarter.", E["arden"], "A5"),
    ("I06", "Support tickets are closed automatically after 30 days of inactivity.", E["tickets"], "A6"),
    ("I07", "The Halden pipeline stores its checkpoints in object storage.", E["halden"], "A7"),
    ("I08", "Two of the four Bramley regions run the new schema.", E["bramley"], "A8"),
]
for item_id, prop, ev, pair in support:
    add(item_id, "clear_direct_support", prop, SUPPORT_USE, ev, relation="supports",
        forbidden=(), expected=(USE,), pair_id=pair, differs="baseline",
        rationale="The passage states the proposition directly, at the same scope and with no temporal qualifier.")

# --- B. clear contradiction (8) — same evidence, proposition negated or altered --------------------------------------
contradict = [
    ("I09", "The Meridian gateway accepts requests of any size.", E["gateway"], "A1", "the size limit is denied"),
    ("I10", "Batch reconciliation at Northwind runs weekly.", E["recon"], "A2", "the frequency is changed"),
    ("I11", "The Kestrel sensor reports temperature in Fahrenheit.", E["kestrel"], "A3", "the unit is changed"),
    ("I12", "Large orders can be dispatched with a single approver.", E["approver"], "A4", "the requirement is denied"),
    ("I13", "The Arden index was 60 in the most recent published quarter.", E["arden"], "A5", "the value is changed"),
    ("I14", "Support tickets are never closed automatically.", E["tickets"], "A6", "the behaviour is denied"),
    ("I15", "Halden pipeline checkpoints are kept on the local disk.", E["halden"], "A7", "the location is changed"),
    ("I16", "All four Bramley regions run the new schema.", E["bramley"], "A8", "the count is changed"),
]
for item_id, prop, ev, pair, differs in contradict:
    add(item_id, "clear_contradiction", prop, SUPPORT_USE, ev, relation="contradicts",
        forbidden=(USE,), expected=(ABSTAIN,), pair_id=pair, differs=differs,
        rationale="The passage asserts the opposite of the proposition, so it can never be cited as support.")

# --- C. partial support (7) — the passage supports part of a conjunctive proposition ---------------------------------
partial = [
    ("I17", "The Meridian gateway rejects requests larger than 8 MB and logs each rejection.", E["gateway"],
     "logging is not mentioned"),
    ("I18", "Batch reconciliation runs nightly and completes within an hour.", E["recon"], "duration is not mentioned"),
    ("I19", "Orders over 500 units require a second approver from a different team.", E["approver"],
     "the approver's team is not mentioned"),
    ("I20", "Halden checkpoints are written to object storage and encrypted at rest.", E["halden"],
     "encryption is not mentioned"),
    ("I21", "Two Bramley regions run the new schema and the migration completes this quarter.", E["bramley"],
     "the completion date is not mentioned"),
    ("I22", "Tickets close after 30 days of inactivity and the requester is notified.", E["tickets"],
     "notification is not mentioned"),
    ("I23", "The Kestrel sensor reports Celsius at 0.1 degree resolution.", E["kestrel"],
     "resolution is not mentioned"),
]
for item_id, prop, ev, differs in partial:
    add(item_id, "partial_support", prop, SUPPORT_USE, ev, relation="partial",
        forbidden=(USE,), expected=(INVESTIGATE,), differs=differs,
        rationale="One conjunct is supported and the other is simply absent from the passage, so the proposition as "
                  "a whole is not established.")

# --- D. scope / qualifier mismatch (7) ------------------------------------------------------------------------------
scope_items = [
    ("I24", "All Northwind scheduled jobs run nightly.", E["recon"], "the subject is widened from one job to all jobs"),
    ("I25", "The Meridian gateway rejects every request larger than 1 MB.", E["gateway"], "the threshold is changed"),
    ("I26", "All orders require a second approver.", E["approver"], "the qualifier over 500 units is dropped"),
    ("I27", "The Arden index is 42.", E["arden"], "the quarter qualifier is dropped"),
    ("I28", "All Halden pipelines store checkpoints in object storage.",
     "Design note: the Halden Ingest pipeline writes its checkpoints to object storage rather than the local disk.",
     "one named pipeline is widened to all pipelines"),
    ("I29", "Across every Northwind product, tickets close after 30 days of inactivity.", E["tickets"],
     "one helpdesk configuration is widened to every product"),
    ("I30", "Every sensor in the Kestrel family reports temperature in Celsius.",
     "Kestrel 3 firmware notes: all temperature values emitted by this sensor are in degrees Celsius.",
     "one firmware version is widened to the whole family"),
]
for item_id, prop, ev, differs in scope_items:
    add(item_id, "scope_qualifier_mismatch", prop, SUPPORT_USE, ev, relation="supports", scope="mismatch",
        forbidden=(USE,), expected=(INVESTIGATE, ABSTAIN), differs=differs,
        rationale="The passage is true of a narrower subject or threshold than the proposition claims, so citing it "
                  "as support would overstate what the evidence covers.")

# --- E. temporal mismatch or supersession (7) -----------------------------------------------------------------------
temporal_items = [
    ("I31", "The Meridian gateway limit is 8 MB.",
     "Operations note 14, superseded by note 21: the gateway rejected bodies above 8 MB. Note 21 raised the limit "
     "to 32 MB in the current release.", "evidence_superseded", (ABSTAIN,), "the passage says it was superseded"),
    ("I32", "The Arden index is 42 this quarter.",
     "Bulletin published three years ago: the Arden index stood at 42 for that quarter.",
     "evidence_predates", (INVESTIGATE, ABSTAIN), "the passage is about an older quarter"),
    ("I33", "Tickets close after 30 days of inactivity.",
     "Former helpdesk configuration, replaced in the March release: tickets with no activity for 30 days were "
     "closed automatically.", "evidence_superseded", (ABSTAIN,), "the configuration was replaced"),
    ("I34", "Two Bramley regions run the new schema.",
     "Migration status as recorded last year: of the four Bramley regions, two had migrated to the new schema.",
     "evidence_predates", (INVESTIGATE, ABSTAIN), "the status is a year old"),
    ("I35", "Orders over 500 units require a second approver.",
     "Policy 7.2 required a second approver for orders above 500 units. Policy 7.2 was withdrawn and replaced by "
     "policy 9.1.", "evidence_superseded", (ABSTAIN,), "the policy was withdrawn"),
    ("I36", "The Halden pipeline stores checkpoints in object storage.",
     "Design note from the original 2019 build: Halden pipeline checkpoints are written to object storage.",
     "evidence_predates", (INVESTIGATE, ABSTAIN), "the note is from an older build"),
    ("I37", "The Kestrel sensor reports temperature in Celsius.",
     "Firmware 2.x emitted temperatures in Celsius. Firmware 3.0 changed the default unit to Fahrenheit.",
     "evidence_superseded", (ABSTAIN,), "a later firmware changed the unit"),
]
for item_id, prop, ev, temporal, expected, differs in temporal_items:
    add(item_id, "temporal_mismatch_or_supersession", prop, SUPPORT_USE, ev, relation="supports",
        temporal=temporal, forbidden=(USE,), expected=expected, differs=differs,
        rationale="The passage may once have supported the proposition but its time relation makes it unsafe to "
                  "cite as current support.")

# --- F. irrelevant evidence (6) -------------------------------------------------------------------------------------
irrelevant = [
    ("I38", "The Meridian gateway rejects requests larger than 8 MB.",
     "Facilities notice: the east car park will be resurfaced over the bank holiday weekend."),
    ("I39", "Batch reconciliation at Northwind runs nightly.",
     "Catering update: the staff canteen now opens at 07:30 on weekdays."),
    ("I40", "The Kestrel sensor reports temperature in Celsius.",
     "Travel policy: rail fares are reimbursed at standard class for journeys under four hours."),
    ("I41", "Orders over 500 units require a second approver.",
     "The office plant rota has been extended to the third floor meeting rooms."),
    ("I42", "The Halden pipeline stores its checkpoints in object storage.",
     "Reminder: the annual fire drill takes place on the first Tuesday of next month."),
    ("I43", "Two of the four Bramley regions run the new schema.",
     "The visitor sign-in tablets were replaced with a newer model last week."),
]
for item_id, prop, ev in irrelevant:
    add(item_id, "irrelevant_evidence", prop, SUPPORT_USE, ev, relation="irrelevant",
        forbidden=(USE,), expected=(ABSTAIN,), differs="unrelated subject matter",
        rationale="The passage has no bearing on the proposition at all.")

# --- G. genuinely ambiguous or unresolved (6) -----------------------------------------------------------------------
ambiguous = [
    ("I44", "The Meridian gateway rejects requests larger than 8 MB.",
     "Two operations notes disagree: note 14 gives the limit as 8 MB and note 15 gives it as 16 MB. Neither note "
     "has been withdrawn.", "the passage contains an unresolved internal conflict"),
    ("I45", "Batch reconciliation at Northwind runs nightly.",
     "The runbook says reconciliation runs on the usual schedule. The usual schedule is not defined anywhere in "
     "this document.", "the referenced schedule is undefined"),
    ("I46", "The Kestrel sensor reports temperature in Celsius.",
     "The firmware notes say the sensor emits temperatures in the configured unit, and the configuration is set "
     "per deployment.", "the answer depends on an unstated configuration"),
    ("I47", "Orders over 500 units require a second approver.",
     "A draft of policy 7.2 mentions a second approver for large orders, but the draft is marked as under review "
     "and the threshold is left blank.", "the passage is a draft with a blank threshold"),
    ("I48", "The Arden index was 42 in the most recent published quarter.",
     "The bulletin reports an index of 42 but does not say which quarter it covers, and two quarters were "
     "published that month.", "the passage does not identify the quarter"),
    ("I49", "The Halden pipeline stores its checkpoints in object storage.",
     "The design note says checkpoints go to durable storage. Durable storage in this system can mean object "
     "storage or the replicated volume.", "the term is genuinely ambiguous"),
]
for item_id, prop, ev, differs in ambiguous:
    add(item_id, "ambiguous_unresolved", prop, SUPPORT_USE, ev, relation="unclear",
        forbidden=(USE,), expected=(INVESTIGATE, ABSTAIN), differs=differs,
        rationale="The passage genuinely fails to settle the proposition; more than one conservative disposition is "
                  "defensible, so no single gold disposition is forced.")

# --- H. semantic-boundary minimal pairs (8 = 4 pairs) ----------------------------------------------------------------
# Each pair differs by exactly one feature and sits on opposite sides of a governance boundary.
add("I50", "boundary_minimal_pair", "The Fenwick job retries failed uploads three times.",
    SUPPORT_USE, "Scheduler note: the Fenwick job retries a failed upload three times before giving up.",
    relation="supports", forbidden=(), expected=(USE,), pair_id="BP1", differs="quantifier matches exactly",
    rationale="Direct support at matching scope; the usable side of the boundary.")
add("I51", "boundary_minimal_pair", "The Fenwick job retries failed uploads at least three times.",
    SUPPORT_USE, "Scheduler note: the Fenwick job retries a failed upload three times before giving up.",
    relation="supports", scope="mismatch", forbidden=(USE,), expected=(INVESTIGATE, ABSTAIN), pair_id="BP1",
    differs="at least widens the quantifier beyond what the passage states",
    rationale="Exactly three is not at least three; the widened quantifier makes the passage insufficient.")

add("I52", "boundary_minimal_pair", "The Corby ledger is reconciled before month end.",
    SUPPORT_USE, "Finance note issued this month: the Corby ledger is reconciled before month end.",
    relation="supports", forbidden=(), expected=(USE,), pair_id="BP2", differs="current note",
    rationale="Current, direct and at matching scope.")
add("I53", "boundary_minimal_pair", "The Corby ledger is reconciled before month end.",
    SUPPORT_USE, "Finance note issued this month: the Corby ledger was reconciled before month end until the "
                 "process moved to quarterly reconciliation in April.",
    relation="supports", temporal="evidence_superseded", forbidden=(USE,), expected=(ABSTAIN,), pair_id="BP2",
    differs="one clause states the practice was superseded",
    rationale="The same sentence, plus a supersession clause, removes its current force.")

add("I54", "boundary_minimal_pair", "The Ashby cache is cleared on deployment.",
    SUPPORT_USE, "Deployment checklist: step 6 clears the Ashby cache.",
    relation="supports", forbidden=(), expected=(USE,), pair_id="BP3", differs="single claim",
    rationale="The passage states exactly the proposition.")
add("I55", "boundary_minimal_pair", "The Ashby cache is cleared on deployment and warmed before traffic returns.",
    SUPPORT_USE, "Deployment checklist: step 6 clears the Ashby cache.",
    relation="partial", forbidden=(USE,), expected=(INVESTIGATE,), pair_id="BP3",
    differs="a second conjunct is added that the passage does not mention",
    rationale="One added conjunct moves the item from usable to partially supported.")

add("I56", "boundary_minimal_pair", "The Dalton report is produced monthly.",
    SUPPORT_USE, "Records note: the Dalton report is not produced monthly.",
    relation="contradicts", forbidden=(USE,), expected=(ABSTAIN,), pair_id="BP4", differs="a plain negation",
    rationale="Flat contradiction.")
add("I57", "boundary_minimal_pair", "The Dalton report is produced monthly.",
    SUPPORT_USE, "Records note: the Dalton report is not always produced monthly.",
    relation="unclear", forbidden=(USE,), expected=(INVESTIGATE, ABSTAIN), pair_id="BP4",
    differs="one hedge word turns the negation into a partial denial",
    rationale="Not always denies universality without settling the general case; more than one conservative "
              "disposition is defensible.")

# --- I. straightforward stable controls (3) --------------------------------------------------------------------------
add("I58", "stable_control", "The Larkin office closes at 18:00 on weekdays.",
    SUPPORT_USE, "Site notice: the Larkin office closes at 18:00 on weekdays.",
    relation="supports", forbidden=(), expected=(USE,), differs="verbatim restatement",
    rationale="Control: an unambiguous, current, exactly scoped restatement.")
add("I59", "stable_control", "The Larkin office closes at 18:00 on weekdays.",
    SUPPORT_USE, "Site notice: the Larkin office closes at 20:00 on weekdays.",
    relation="contradicts", forbidden=(USE,), expected=(ABSTAIN,), differs="one differing number",
    rationale="Control: an unambiguous contradiction.")
add("I60", "stable_control", "The Larkin office closes at 18:00 on weekdays.",
    SUPPORT_USE, "Site notice: the staff bicycle shelter has been relocated to the north entrance.",
    relation="irrelevant", forbidden=(USE,), expected=(ABSTAIN,), differs="unrelated notice",
    rationale="Control: plainly unrelated evidence.")


def digest(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    assert len(ITEMS) == 60, f"expected 60 items, built {len(ITEMS)}"
    assert len({i['item_id'] for i in ITEMS}) == 60, "duplicate item ids"
    for item in ITEMS:
        assert item["proposition"].strip() and item["evidence"].strip(), item["item_id"]
    corpus = {"experiment_id": "G-EVID1", "contract_version": "g-evid1.0", "item_count": len(ITEMS), "items": ITEMS}
    gold = {"experiment_id": "G-EVID1", "contract_version": "g-evid1.0", "item_count": len(GOLD), "gold": GOLD}
    (OUT / "corpus.json").write_text(json.dumps(corpus, indent=1, ensure_ascii=False), encoding="utf-8")
    (OUT / "gold.json").write_text(json.dumps(gold, indent=1, ensure_ascii=False), encoding="utf-8")

    families: dict[str, int] = {}
    for row in GOLD:
        families[row["family"]] = families.get(row["family"], 0) + 1
    print(json.dumps({"items": len(ITEMS), "families": families,
                      "corpus_sha256": digest(corpus), "gold_sha256": digest(gold),
                      "use_forbidden_items": sum(1 for g in GOLD if "use" in g["forbidden_dispositions"]),
                      "use_allowed_items": sum(1 for g in GOLD if "use" not in g["forbidden_dispositions"])},
                     indent=1))


if __name__ == "__main__":
    main()
