from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

from historical_memory_truth import build_historical_memory_truth
from memory_commit_attribution import build_memory_commit_attribution
from memory_provenance_integrity import (
    PROVENANCE_CLASSES, bounded_fact_conflicts, classify_memory_provenance,
    prepare_memory_for_ingestion, public_provenance_explanation,
)

CHECKS=[]
def require(name, condition, detail=""):
    CHECKS.append((name,bool(condition),detail))
    if not condition: raise AssertionError(f"{name}: {detail}")


def _attribution(role: str, content: str, suffix: str):
    return build_memory_commit_attribution(
        role=role, operation_id=f"conversation_20260813T030000_{suffix}",
        session_id=f"session_{suffix}", turn_id=f"turn_{suffix}", source="fixture",
        content=content, completion_state="completed",
        provider_generation_completed=(role=="assistant"), operation_completion_claimed=True,
    )


def test_classes_and_validation():
    require("0011-explicit-classes", tuple(PROVENANCE_CLASSES)==("user","assistant","action_receipt","imported","unknown"), PROVENANCE_CLASSES)
    user_text="I prefer the synthetic Cedar layout."
    user={"id":"u1","content":user_text,"memory_commit_attribution":_attribution("user",user_text,"b2u1")}
    assistant_text="I can remind you about the Cedar layout."
    assistant={"id":"a1","content":assistant_text,"memory_commit_attribution":_attribution("assistant",assistant_text,"b2a1")}
    require("0012-user-attribution-valid", classify_memory_provenance(user).historical_evidence_eligible)
    require("0014-assistant-not-user-evidence", not classify_memory_provenance(assistant).historical_evidence_eligible)
    bad=dict(user); bad["content"]="tampered content"
    prepared=prepare_memory_for_ingestion(bad)
    require("0012-digest-invalid", prepared["provenance_integrity"]["attribution_digest_valid"] is False, prepared)
    require("0013-malformed-quarantined", prepared.get("provenance_quarantined") is True and not prepared.get("historical_evidence_eligible"), prepared)
    imported=prepare_memory_for_ingestion({"id":"imp1","content":"synthetic imported fact","source":"imported_archive","provenance":{"origin":"imported"}})
    require("0011-imported-class", imported["provenance_integrity"]["provenance_class"]=="imported", imported)
    unknown=prepare_memory_for_ingestion({"id":"x1","type":"thought","content":"internal synthetic thought"})
    require("0011-unknown-class", unknown["provenance_integrity"]["provenance_class"]=="unknown" and not unknown.get("provenance_quarantined"), unknown)


def test_corrections_supersession_and_conflicts():
    older={"id":"old1","type":"conversation_user","source":"operator_fixture","operator_explicit":True,"fact_key":"fixture_color","content":"The fixture color is blue."}
    correction={"id":"new1","type":"conversation_user","source":"operator_fixture","operator_explicit":True,"operator_correction":True,"fact_key":"fixture_color","content":"The fixture color is not blue; it is amber."}
    prepared=prepare_memory_for_ingestion(correction, existing_records=[older])
    require("0015-user-correction-eligible", prepared.get("historical_evidence_eligible") is True, prepared)
    lineage=prepared.get("supersession_lineage") or {}
    require("0016-supersession-lineage", lineage.get("superseded_record_count")==1 and "old1" in lineage.get("superseded_record_ids",[]), lineage)
    require("0016-superseded-digest", hashlib.sha256(older["content"].encode()).hexdigest() in prepared.get("superseded_content_digests",[]), prepared)
    conflicts=bounded_fact_conflicts([older, correction])
    require("0017-fact-conflict", len(conflicts)==1 and conflicts[0]["distinct_content_digest_count"]==2, conflicts)
    require("0017-conflict-content-free", "blue" not in str(conflicts) and "amber" not in str(conflicts), conflicts)


def test_rejections_and_history_truth():
    assistant={"id":"asst-reminder","type":"conversation_eidolon","source":"conversation_session","conversation_session_id":"s","content":"I can help with synthetic scheduling reminders."}
    prepared=prepare_memory_for_ingestion(assistant)
    explanation=public_provenance_explanation(prepared)
    require("0018-operator-explanation", explanation["content_free"] and "Assistant-authored" in explanation["operator_explanation"], explanation)
    require("0018-no-private-text", "scheduling" not in str(explanation), explanation)
    profile=build_historical_memory_truth("What difficulties have we had with synthetic scheduling reminders?", [prepared])
    require("0014-assistant-summary-not-history", profile.state=="assistant_authored_non_evidence" and profile.uncertainty_required, profile.public_summary())


def test_malformed_ambiguous_superseded_conflicting_fixtures():
    malformed=prepare_memory_for_ingestion({"type":"conversation_user","content":"Synthetic malformed user history."})
    ambiguous=prepare_memory_for_ingestion({"id":"amb1","content":"Synthetic untyped history."})
    older={"id":"fact1","type":"conversation_user","source":"operator_fixture","operator_explicit":True,"fact_key":"bounded_key","content":"The bounded item is alpha."}
    newer=prepare_memory_for_ingestion({"id":"fact2","type":"conversation_user","source":"operator_fixture","operator_explicit":True,"operator_correction":True,"fact_key":"bounded_key","content":"The bounded item is beta."}, existing_records=[older])
    require("0019-malformed", malformed.get("provenance_quarantined") is True, malformed)
    require("0019-ambiguous-unknown", ambiguous["provenance_integrity"]["provenance_class"]=="unknown", ambiguous)
    require("0019-superseded", bool(newer.get("supersession_lineage")), newer)
    require("0019-conflicting", len(bounded_fact_conflicts([older,newer]))==1)


def main():
    for fn in (test_classes_and_validation,test_corrections_supersession_and_conflicts,test_rejections_and_history_truth,test_malformed_ambiguous_superseded_conflicting_fixtures): fn()
    print(f"v1489.0011-.0020 memory provenance integrity: {len(CHECKS)}/{len(CHECKS)} checks passed")
    for n,o,_ in CHECKS: print(f"  {'PASS' if o else 'FAIL'} {n}")
if __name__=='__main__': main()
