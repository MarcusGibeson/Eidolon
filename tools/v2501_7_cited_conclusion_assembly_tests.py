from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from conscious_agent.bounded_research_reasoning import assemble_cited_conclusion
checks=[]
def req(v,n):checks.append(n);assert v,n
comparison={"claims":[
 {"claim_code":"rq1","state":"supported","supporting_citations":["c1"],"refuting_citations":[],"all_independent_citations":["c1"],"max_quality":.95,"max_relevance":.9},
 {"claim_code":"rq2","state":"supported","supporting_citations":["c2"],"refuting_citations":[],"all_independent_citations":["c2"],"max_quality":.5,"max_relevance":.6},
 {"claim_code":"rq3","state":"conflicted","supporting_citations":["c3"],"refuting_citations":["c4"],"all_independent_citations":["c3","c4"],"max_quality":.9,"max_relevance":.9},
 {"claim_code":"rq4","state":"stale_only","supporting_citations":[],"refuting_citations":[],"all_independent_citations":["c5"],"max_quality":.9,"max_relevance":.9},
]}
citations=[{"citation_id":f"c{i}","public_url":f"https://s{i}.example/report","source_digest":str(i)*64} for i in range(1,6)]
report=assemble_cited_conclusion(comparison,claim_labels={"rq1":"verified public fact","rq2":"tentative public inference","rq3":"contested public claim","rq4":"old public claim"},citations=citations)
req(len(report["verified_findings"])==1 and report["verified_findings"][0]["citations"]==["c1"],"verified_findings_cited")
req(len(report["reasonable_inferences"])==1 and report["reasonable_inferences"][0]["citations"]==["c2"],"reasonable_inference_distinguished")
req(len(report["unresolved_disagreements"])==1 and report["unresolved_disagreements"][0]["refuting_citations"]==["c4"],"disagreement_not_collapsed")
req(len(report["missing_evidence"])==1 and report["missing_evidence"][0]["reason"]=="stale evidence only","stale_limitation_visible")
req(report["externally_verifiable_claims_traceable"] and report["citation_count"]==5,"every_external_claim_traceable")
req("Verified findings:" in report["rendered_answer"] and "Unresolved disagreement" in report["rendered_answer"],"readable_sectioned_answer_assembled")
req(report["generated_prose_is_evidence"] is False and report["raw_page_content_persisted"] is False and report["raw_query_text_exposed"] is False,"synthesis_not_promoted_to_evidence")
print(json.dumps({"suite":"v2501.7-cited-conclusion-assembly","ok":True,"passed":len(checks),"failed":0,"checks":checks},sort_keys=True))
