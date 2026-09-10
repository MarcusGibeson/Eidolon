from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from conscious_agent.bounded_research_reasoning import compare_cross_source_evidence
checks=[]
def req(v,n):checks.append(n);assert v,n
def row(cid,src,evid,stance,fresh="fresh",q=.9):return {"claim_code":"rq1","citation_id":cid,"source_identity":src,"source_digest":"a"*64,"evidence_digest":evid*64,"stance":stance,"freshness":fresh,"quality_score":q,"relevance_score":.8}
extraction={"evidence":[row("s1","one.example","1","supports"),row("s1-copy","mirror.example","1","supports"),row("r1","two.example","2","refutes"),row("old","three.example","3","supports","stale"),row("unknown","four.example","4","unknown")]}
result=compare_cross_source_evidence(extraction);claim=result["claims"][0]
req(claim["state"]=="conflicted" and claim["contradiction_preserved"],"support_and_refutation_remain_conflicted")
req(claim["duplicate_evidence_count"]==1,"duplicate_content_detected_across_sources")
req(claim["repetition_counts_as_independent_confirmation"] is False,"repetition_not_independent_confirmation")
req("old" in claim["stale_citations"] and "unknown" in claim["incomplete_citations"],"stale_and_incomplete_evidence_remain_visible")
req(claim["independent_evidence_count"]==4,"duplicate_removed_from_independent_count")
req(result["contradictions_averaged_away"] is False and result["conflicted_claim_codes"]==["rq1"],"contradiction_summary_explicit")
print(json.dumps({"suite":"v2501.6-cross-source-comparison","ok":True,"passed":len(checks),"failed":0,"checks":checks},sort_keys=True))
