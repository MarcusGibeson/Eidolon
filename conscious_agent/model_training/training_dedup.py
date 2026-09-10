from __future__ import annotations
"""Exact/near duplicate and diversity controls for approved training evidence."""
import hashlib, json, math, re
from collections import Counter,defaultdict
from typing import Any, Iterable, Mapping
from model_training.training_schema import normalize_training_record
CONTRACT_VERSION="v2503.4.28.2"

def _tokens(v: Any)->set[str]:
    s=v if isinstance(v,str) else json.dumps(v,ensure_ascii=True,sort_keys=True)
    return set(re.findall(r"[a-z0-9_]+",s.lower()))
def _content_tokens(n: Mapping[str,Any])->set[str]:
    return _tokens(n["input"])|_tokens(n["chosen_output"])
def _digest_payload(n: Mapping[str,Any])->str:
    return hashlib.sha256(json.dumps({"capability":n["capability"],"input":n["input"],"chosen":n["chosen_output"]},ensure_ascii=True,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def exact_content_digest(record: Mapping[str,Any])->str:
    return _digest_payload(normalize_training_record(record))
def similarity(a: Mapping[str,Any],b: Mapping[str,Any])->float:
    na,nb=normalize_training_record(a),normalize_training_record(b)
    if na["capability"]!=nb["capability"]: return 0.0
    ta=_content_tokens(na); tb=_content_tokens(nb)
    return 1.0 if not ta and not tb else (len(ta&tb)/max(1,len(ta|tb)))
def deduplicate_records(records: Iterable[Mapping[str,Any]], *, near_threshold: float=.92, max_per_fingerprint:int=3)->dict[str,Any]:
    threshold=max(0.0,min(1.0,float(near_threshold)))
    kept=[]; kept_norm=[]; kept_tokens=[]; rejected=[]; exact=set(); fingerprints=Counter(); token_index=defaultdict(list); empty_by_cap=defaultdict(list)
    for r in records:
        n=normalize_training_record(r); d=_digest_payload(n); fp=n["semantic_fingerprint"]; cap=n["capability"]; tokens=_content_tokens(n)
        reason=None
        if d in exact: reason="exact_duplicate"
        elif fingerprints[fp]>=max_per_fingerprint: reason="frequency_cap"
        else:
            if not tokens:
                candidates=list(empty_by_cap[cap])
            else:
                # Jaccard >= threshold implies a candidate may omit at most
                # floor(len(A)*(1-threshold)) tokens from A. Probe one more
                # than that many least-common tokens, guaranteeing any true
                # near duplicate appears in at least one posting list.
                max_misses=math.floor(len(tokens)*(1.0-threshold)+1e-12)
                probe_count=min(len(tokens),max_misses+1)
                probes=sorted(tokens,key=lambda tok:(len(token_index[(cap,tok)]),tok))[:probe_count]
                candidate_ids=set()
                for tok in probes: candidate_ids.update(token_index[(cap,tok)])
                candidates=sorted(candidate_ids)
            for idx in candidates:
                other=kept_tokens[idx]
                # Cheap necessary size-ratio bound before exact Jaccard.
                if threshold>0 and other:
                    small=min(len(tokens),len(other)); large=max(len(tokens),len(other))
                    if small/large < threshold: continue
                score=1.0 if not tokens and not other else len(tokens&other)/max(1,len(tokens|other))
                if score>=threshold: reason="near_duplicate"; break
        if reason:
            rejected.append({"record_id":n["record_id"],"reason":reason})
        else:
            idx=len(kept); kept.append(r); kept_norm.append(n); kept_tokens.append(tokens); exact.add(d); fingerprints[fp]+=1
            if not tokens: empty_by_cap[cap].append(idx)
            else:
                for tok in tokens: token_index[(cap,tok)].append(idx)
    caps=Counter(n["capability"] for n in kept_norm)
    return {"ok":True,"contract_version":CONTRACT_VERSION,"kept_records":kept,"kept_count":len(kept),"rejected":rejected,"capability_counts":dict(sorted(caps.items())),"model_training_authorized":False}
