from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1268_fixture import verified_chain
from operator_review_handoff_foundations import prepare_operator_review_handoff
from operator_review_handoff import record_operator_review_decision

def approved_chain(base:Path):
    chain=verified_chain(base);review_rt=base/'review'
    packet=prepare_operator_review_handoff(chain['repair']['repair_id'],chain['source'],self_modification_runtime_root=chain['sm'],test_selection_runtime_root=chain['ts'],repair_runtime_root=chain['rr'],runtime_root=review_rt)
    decision=record_operator_review_decision(packet['review_id'],packet_digest=packet['record_digest'],decision='approve_for_v1269_consideration',runtime_root=review_rt)
    return {**chain,'review_rt':review_rt,'packet':packet,'decision':decision}
