from __future__ import annotations
from conscious_agent.inquiry_evidence_quality import InquiryEvidenceQuality
from conscious_agent.inquiry_reflection import InquiryReflection
import json, tempfile
from pathlib import Path
from conscious_agent.persistent_motivation import MotivationStore
from conscious_agent.self_directed_inquiry import InquiryWorkspace
from conscious_agent.inquiry_evidence_assimilation import InquiryEvidenceLedger

def setup_case():
    td=tempfile.TemporaryDirectory(); r=Path(td.name)/"cognition"; m=MotivationStore(r)
    mr=m.record_motivation("mot",kind="curiosity",summary="Understand the observed pattern",cognitive_state="desire",urgency=.8,confidence=.7,origin_type="fixture",origin_ref="fixture")
    mid=mr["result"]["motivation_id"]; w=InquiryWorkspace(r,motivation_store=m)
    ir=w.create_inquiry("inq",motivation_id=mid,question="What best explains the observed pattern?",uncertainty=.7,sources_sought=["operator evidence"])
    return td,r,w,ir["result"]["inquiry_id"]

def finish(results):
    passed=sum(1 for x in results if x[1]); payload={"passed":passed,"total":len(results),"results":[{"name":n,"passed":ok,"detail":d} for n,ok,d in results]};print(json.dumps(payload,sort_keys=True));raise SystemExit(0 if passed==len(results) else 1)

def main():
 td,r,w,i=setup_case(); ledger=InquiryEvidenceLedger(r,workspace=w); ledger.assimilate("e1",inquiry_id=i,summary="Strong evidence",source_label="source-a",reliability=1,supports="supports"); q=InquiryEvidenceQuality(r,ledger=ledger,workspace=w);q.assess("a",inquiry_id=i); ref=InquiryReflection(r,workspace=w,quality=q); x=ref.reflect("r",inquiry_id=i); d=ref.reflect("r",inquiry_id=i); s=ref.inspection_summary(); row=s["recent_reflections"][0]
 results=[("recorded",x["status"]=="inquiry_reflection_recorded",str(x)),("conclusion",bool(x["result"]["authored_conclusion"]),str(x)),("bounded",0<=x["result"]["uncertainty"]<=1,str(x)),("dedup",d["idempotent"],str(d)),("one",s["reflection_count"]==1,str(s)),("provider",not row["provider_contacted"],str(row)),("hidden",not row["hidden_reasoning_stored"],str(row)),("browse",not row["external_browsing_performed"],str(row)),("authority",not row["action_authorized"],str(row)),("refs",len(row["supporting_reference_digests"])==1,str(row)),("inspection",not s["action_authority_changed"],str(s))];td.cleanup();finish(results)
if __name__=="__main__":main()
