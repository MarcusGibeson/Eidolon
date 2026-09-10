from __future__ import annotations
from conscious_agent.inquiry_evidence_quality import InquiryEvidenceQuality
from conscious_agent.inquiry_reflection import InquiryReflection
from conscious_agent.inquiry_resolution import InquiryResolution
from conscious_agent.belief_revision import BeliefRevisionStore
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
 td,r,w,i=setup_case(); ledger=InquiryEvidenceLedger(r,workspace=w);ledger.assimilate("e1",inquiry_id=i,summary="Strong evidence",source_label="source-a",reliability=1,supports="supports");ledger.assimilate("e2",inquiry_id=i,summary="Corroboration",source_label="source-b",reliability=1,supports="supports");q=InquiryEvidenceQuality(r,ledger=ledger,workspace=w);q.assess("a",inquiry_id=i);ref=InquiryReflection(r,workspace=w,quality=q);ref.reflect("r",inquiry_id=i);b=BeliefRevisionStore(r);res=InquiryResolution(r,workspace=w,reflection=ref,beliefs=b);x=res.resolve("z",inquiry_id=i,proposition="The observed pattern has a supported explanation.",residual_question="Will it generalize?");d=res.resolve("z",inquiry_id=i,proposition="The observed pattern has a supported explanation.");s=res.inspection_summary();inq=next(v for v in w.snapshot()["inquiries"] if v["inquiry_id"]==i);belief=b.snapshot()["beliefs"][0];row=s["recent_resolutions"][0]
 results=[("resolved",x["status"]=="inquiry_resolved",str(x)),("belief",bool(x["result"]["belief_id"]),str(x)),("completed",inq["status"]=="completed",str(inq)),("residual",x["result"]["residual_question_preserved"],str(x)),("uncertainty",row["uncertainty_retained"]<=.4,str(row)),("belief origin",belief["origin"]["type"]=="inquiry_resolution",str(belief)),("dedup",d["idempotent"],str(d)),("one",s["resolution_count"]==1,str(s)),("provider",not row["provider_contacted"],str(row)),("hidden",not row["hidden_reasoning_stored"],str(row)),("authority",not row["action_authorized"] and not row["action_executed"],str(row)),("inspection",not s["action_authority_changed"],str(s))];td.cleanup();finish(results)
if __name__=="__main__":main()
