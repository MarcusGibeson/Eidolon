from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from conscious_agent.bounded_research_reasoning import extract_claim_evidence
from conscious_agent.research_web_intelligence_v2100 import NATIVE_RECEIPT_CONTRACT_VERSION
checks=[]
def req(v,n):checks.append(n);assert v,n
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
def receipt(cid,stance,evidence,quality=.9,fresh=True):
 r={"contract_version":NATIVE_RECEIPT_CONTRACT_VERSION,"receipt_kind":"source_observation","authoritative":True,"terminal":True,"operation_digest":"8"*64,"terminal_result_digest":"9"*64,"source_observed":True,"plan_digest":"1"*64,"source_candidate_digest":hashlib.sha256(cid.encode()).hexdigest(),"claim_code":"rq1","stance":stance,"evidence_digest":hashlib.sha256(evidence.encode()).hexdigest(),"citation_id":cid,"source_kind":"primary_official","quality_score":quality,"freshness_known":True,"fresh_enough":fresh,"relevance_score":.85,"observed_bytes":123}
 r["receipt_digest"]=digest(r);return r
one=receipt("c1","supports","e1")
two=receipt("c2","refutes","e2",quality=.8,fresh=False)
tampered=dict(receipt("bad","supports","bad"));tampered["stance"]="refutes"
result=extract_claim_evidence(plan_digest="1"*64,observations=[one,two,tampered],citation_context={"c1":{"public_url":"https://docs.example/report?secret=gone","host":"docs.example"},"c2":{"public_url":"https://archive.example/report#frag","host":"archive.example"}})
req(result["ok"] and result["evidence_count"]==2,"only_valid_signed_observations_admitted")
req(result["evidence"][0]["stance"]=="supports" and result["evidence"][1]["stance"]=="refutes","claim_stance_preserved")
req(result["evidence"][0]["freshness"]=="fresh" and result["evidence"][1]["freshness"]=="stale","freshness_preserved")
req(all("?" not in x["public_url"] and "#" not in x["public_url"] for x in result["evidence"]),"citation_urls_sanitized")
req(all(x["raw_page_content_persisted"] is False and x["raw_quote_persisted"] is False for x in result["evidence"]),"raw_content_never_persisted")
req(all(0<=x["uncertainty"]<=1 and 0<=x["relevance_score"]<=1 and 0<=x["quality_score"]<=1 for x in result["evidence"]),"quality_relevance_uncertainty_bounded")
req(len(result["evidence_extraction_digest"])==64 and result["signed_observation_receipts_required"],"extraction_digest_and_receipt_binding")
print(json.dumps({"suite":"v2501.5-evidence-extraction","ok":True,"passed":len(checks),"failed":0,"checks":checks},sort_keys=True))
