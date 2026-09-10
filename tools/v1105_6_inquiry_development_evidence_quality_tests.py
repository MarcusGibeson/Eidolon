from __future__ import annotations
from conscious_agent.inquiry_evidence_quality import InquiryEvidenceQuality
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
 td,r,w,i=setup_case(); ledger=InquiryEvidenceLedger(r,workspace=w)
 e1=ledger.assimilate("e1",inquiry_id=i,summary="First observation supports the pattern",source_label="source-a",reliability=.9,supports="supports")
 e2=ledger.assimilate("e2",inquiry_id=i,summary="Independent observation supports it",source_label="source-b",reliability=.8,supports="supports")
 q=InquiryEvidenceQuality(r,ledger=ledger,workspace=w); a=q.assess("assess",inquiry_id=i); d=q.assess("assess",inquiry_id=i); s=q.inspection_summary(); snap=w.snapshot(); row=next(x for x in snap["inquiries"] if x["inquiry_id"]==i)
 results=[("assessed",a["status"]=="evidence_quality_assessed",str(a)),("count",a["result"]["active_evidence_count"]==2,str(a)),("sources",a["result"]["independent_source_count"]==2,str(a)),("quality",a["result"]["quality_score"]>0,str(a)),("uncertainty",a["result"]["updated_uncertainty"]<.7,str(a)),("workspace updated",row["uncertainty"]<.7,str(row)),("dedup",d["idempotent"],str(d)),("inspection",s["assessment_count"]==1,str(s)),("no browse",not s["external_browsing_performed"],str(s)),("no authority",not s["action_authority_changed"],str(s))];td.cleanup();finish(results)
if __name__=="__main__":main()
