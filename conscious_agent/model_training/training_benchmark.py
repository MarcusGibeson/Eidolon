from __future__ import annotations
"""Operator-authorized model execution over a frozen evaluation corpus."""
import time
from typing import Any, Callable, Mapping
from model_training.training_eval import validate_evaluation_corpus, score_evaluation_results
CONTRACT_VERSION='v2503.4.30.1'

def run_frozen_corpus(*, corpus: Mapping[str,Any], model_id: str, provider_generate: Callable[[str],str]|None, operator_authorized: bool, check_runner: Callable[[Mapping[str,Any],str],Mapping[str,Any]]|None=None) -> dict[str,Any]:
    if operator_authorized is not True: return {'ok':False,'status':'benchmark_operator_authorization_required','provider_contacted':False,'model_training_authorized':False}
    if not validate_evaluation_corpus(corpus): return {'ok':False,'status':'benchmark_corpus_invalid','provider_contacted':False,'model_training_authorized':False}
    if provider_generate is None: return {'ok':False,'status':'benchmark_provider_required','provider_contacted':False,'model_training_authorized':False}
    if not str(model_id or '').strip(): return {'ok':False,'status':'benchmark_model_id_required','provider_contacted':False,'provider_request_count':0,'model_training_authorized':False}
    results=[]; provider_requests=0
    for case in corpus.get('cases',[]):
        started=time.perf_counter(); prompt=str(case.get('prompt') or '')
        try:
            provider_requests+=1
            output=str(provider_generate(prompt))
            verdict=dict(check_runner(case,output)) if check_runner else {'passed':bool(output.strip()),'violations':[]}
            passed=verdict.get('passed') is True; violations=list(verdict.get('violations') or [])
            error=''
        except Exception as exc:
            output=''; passed=False; violations=['provider_or_check_failure']; error=type(exc).__name__
        results.append({'case_id':case.get('case_id'),'passed':passed,'violations':violations,'latency_ms':round((time.perf_counter()-started)*1000,3),'error_type':error})
    scored=score_evaluation_results(corpus,results,model_id=model_id)
    return {'ok':bool(scored.get('complete')),'status':'benchmark_complete' if scored.get('complete') else 'benchmark_incomplete','evaluation':scored,'result_count':len(results),'provider_contacted':provider_requests>0,'provider_request_count':provider_requests,'raw_model_outputs_returned':False,'model_training_authorized':False,'model_promotion_authorized':False}
