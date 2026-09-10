from __future__ import annotations
"""Frozen holdout corpus, baseline scoring, and deterministic model comparison scaffolding."""
import hashlib,json
from collections import Counter
from typing import Any, Iterable, Mapping
CONTRACT_VERSION="v2503.4.28.2"
def _digest(v:Any)->str: return hashlib.sha256(json.dumps(v,ensure_ascii=True,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def _hex64(v:Any)->bool:
    s=str(v or ""); return len(s)==64 and all(c in "0123456789abcdefABCDEF" for c in s)
def validate_evaluation_corpus(corpus:Mapping[str,Any])->bool:
    if not isinstance(corpus,Mapping) or corpus.get("frozen") is not True: return False
    version=str(corpus.get("corpus_version") or "").strip(); cases=corpus.get("cases")
    if not version or not isinstance(cases,list): return False
    ids=[]
    for row in cases:
        if not isinstance(row,Mapping): return False
        cid=str(row.get("case_id") or "").strip(); capability=str(row.get("capability") or "").strip()
        if not cid or not capability or "prompt" not in row or not isinstance(row.get("checks"),list): return False
        ids.append(cid)
    if len(ids)!=len(set(ids)): return False
    content={"corpus_version":version,"cases":cases}
    try: case_count=int(corpus.get("case_count"))
    except (TypeError,ValueError): return False
    return _hex64(corpus.get("corpus_digest")) and _digest(content)==str(corpus.get("corpus_digest")) and case_count==len(cases)
def freeze_evaluation_corpus(cases: Iterable[Mapping[str,Any]], *, corpus_version:str)->dict[str,Any]:
    rows=[]; ids=set(); version=str(corpus_version).strip()
    if not version: raise ValueError("evaluation_corpus_version_required")
    for raw in cases:
        row=dict(raw); cid=str(row.get("case_id") or "")
        if not cid or cid in ids: raise ValueError("evaluation_case_id_missing_or_duplicate")
        if not row.get("capability") or "prompt" not in row or not isinstance(row.get("checks"),list): raise ValueError("evaluation_case_incomplete")
        ids.add(cid); rows.append(row)
    content={"corpus_version":version,"cases":rows}; digest=_digest(content)
    return {"contract_version":"v2503.4.24","frozen":True,"corpus_version":version,"case_count":len(rows),"cases":rows,"corpus_digest":digest,"model_training_authorized":False}
def _seal_evaluation(payload:Mapping[str,Any])->dict[str,Any]:
    row=dict(payload); row["evaluation_digest"]=_digest({k:v for k,v in row.items() if k!="evaluation_digest"}); return row
def validate_evaluation_result(result:Mapping[str,Any], *, corpus:Mapping[str,Any]|None=None)->bool:
    if not isinstance(result,Mapping) or not _hex64(result.get("evaluation_digest")) or not _hex64(result.get("corpus_digest")): return False
    if str(result.get("evaluation_digest"))!=_digest({k:v for k,v in result.items() if k!="evaluation_digest"}): return False
    if not str(result.get("model_id") or "").strip(): return False
    try: passed=int(result.get("passed")); total=int(result.get("total")); score=float(result.get("score"))
    except (TypeError,ValueError): return False
    if passed<0 or total<0 or passed>total or abs(score-round(100*passed/max(1,total),3))>0.001: return False
    violations=result.get("violation_counts")
    if not isinstance(violations,Mapping): return False
    for k,v in violations.items():
        if not str(k).strip(): return False
        try: n=int(v)
        except (TypeError,ValueError): return False
        if n<0: return False
    if not isinstance(result.get("complete"),bool): return False
    if corpus is not None:
        if not validate_evaluation_corpus(corpus): return False
        if result.get("corpus_digest")!=corpus.get("corpus_digest") or total!=int(corpus.get("case_count") or 0): return False
    return True
def score_evaluation_results(corpus:Mapping[str,Any], results:Iterable[Mapping[str,Any]], *, model_id:str)->dict[str,Any]:
    model=str(model_id).strip()
    if not validate_evaluation_corpus(corpus): return _seal_evaluation({"contract_version":"v2503.4.25","model_id":model,"corpus_digest":str(corpus.get("corpus_digest") or ""),"passed":0,"total":0,"score":0.0,"violation_counts":{},"mean_latency_ms":None,"complete":False,"status":"evaluation_corpus_invalid","model_training_authorized":False})
    expected={str(c["case_id"]):c for c in corpus.get("cases",[]) if isinstance(c,Mapping)}; rows=list(results); ids=[str(r.get("case_id")) for r in rows if isinstance(r,Mapping)]
    duplicate_ids=len(ids)!=len(set(ids)); got={str(r.get("case_id")):dict(r) for r in rows if isinstance(r,Mapping)}; passed=0; violations=Counter(); latency=[]
    for cid in expected:
        r=got.get(cid,{})
        if r.get("passed") is True: passed+=1
        for v in r.get("violations",[]) if isinstance(r.get("violations"),list) else []: violations[str(v)]+=1
        if isinstance(r.get("latency_ms"),(int,float)): latency.append(float(r["latency_ms"]))
    total=len(expected); complete=(not duplicate_ids and set(got)==set(expected) and all(isinstance(got[cid].get("passed"),bool) for cid in expected))
    return _seal_evaluation({"contract_version":"v2503.4.25","model_id":model,"corpus_digest":str(corpus.get("corpus_digest") or ""),"passed":passed,"total":total,"score":round(100*passed/max(1,total),3),"violation_counts":dict(sorted(violations.items())),"mean_latency_ms":round(sum(latency)/max(1,len(latency)),3) if latency else None,"complete":complete,"duplicate_result_ids":duplicate_ids,"model_training_authorized":False})
def compare_model_evaluations(baseline:Mapping[str,Any], candidate:Mapping[str,Any])->dict[str,Any]:
    if baseline.get("corpus_digest")!=candidate.get("corpus_digest"): return {"ok":False,"status":"comparison_corpus_mismatch"}
    b=float(baseline.get("score") or 0); c=float(candidate.get("score") or 0); bv=dict(baseline.get("violation_counts") or {}); cv=dict(candidate.get("violation_counts") or {})
    no_category_regression=all(int(cv.get(k,0))<=int(bv.get(k,0)) for k in set(bv)|set(cv))
    promotion_eligible=bool(baseline.get("complete") and candidate.get("complete") and c>=b and no_category_regression and c-b>=5.0)
    return {"ok":True,"contract_version":"v2503.4.26","baseline_model_id":baseline.get("model_id"),"candidate_model_id":candidate.get("model_id"),"score_delta":round(c-b,3),"violation_delta":sum(cv.values())-sum(bv.values()),"no_violation_category_regression":no_category_regression,"promotion_eligible":promotion_eligible,"operator_approval_required":True,"model_promotion_authorized":False}
def _materialize_immutable(path, payload, *, conflict_status):
    from model_training.training_record import _atomic_json
    if path.exists():
        try: existing=json.loads(path.read_text(encoding="utf-8"))
        except Exception: existing={}
        if existing==payload: return True,"restored"
        return False,conflict_status
    _atomic_json(path,payload); return True,"created"
def materialize_evaluation_corpus(*, runtime_root, corpus_version: str, cases: Iterable[Mapping[str,Any]], operator_authorized: bool) -> dict[str,Any]:
    from model_training.training_record import _training_root
    if operator_authorized is not True: return {"ok":False,"status":"evaluation_corpus_operator_authorization_required","model_training_authorized":False}
    corpus=freeze_evaluation_corpus(cases,corpus_version=corpus_version); safe="".join(c if c.isalnum() or c in "._-" else "-" for c in corpus_version)[:96]; path=_training_root(runtime_root)/"eval"/f"{safe}.corpus.json"; ok,state=_materialize_immutable(path,corpus,conflict_status="evaluation_corpus_version_conflict")
    return {"ok":ok,"status":"evaluation_corpus_frozen" if ok else state,"corpus":corpus if ok else {},"runtime_path":str(path),"model_training_authorized":False}
def materialize_evaluation_result(*, runtime_root, corpus:Mapping[str,Any], results:Iterable[Mapping[str,Any]], model_id:str, operator_authorized:bool)->dict[str,Any]:
    from model_training.training_record import _training_root
    if operator_authorized is not True: return {"ok":False,"status":"evaluation_result_operator_authorization_required","model_training_authorized":False}
    scored=score_evaluation_results(corpus,results,model_id=model_id)
    if scored.get("status")=="evaluation_corpus_invalid": return {"ok":False,"status":"evaluation_corpus_invalid","model_training_authorized":False}
    safe="".join(c if c.isalnum() or c in "._-" else "-" for c in str(model_id))[:96]; path=_training_root(runtime_root)/"eval"/f"{safe}.{str(corpus.get('corpus_digest') or '')[:12]}.result.json"; ok,state=_materialize_immutable(path,scored,conflict_status="evaluation_result_identity_conflict")
    return {"ok":ok,"status":"evaluation_result_materialized" if ok else state,"evaluation":scored if ok else {},"runtime_path":str(path),"model_training_authorized":False}
