from pathlib import Path
import sys,json,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT)]
from conscious_agent.model_training.training_record import create_training_record,_seal
from conscious_agent.model_training.training_sanitizer import sanitize_training_record
from conscious_agent.model_training.training_dataset import DEFAULT_CAPS,build_dataset_manifest,validate_dataset_manifest,materialize_dataset_manifest
from conscious_agent.model_training.training_eval import freeze_evaluation_corpus,validate_evaluation_corpus,score_evaluation_results,compare_model_evaluations,materialize_evaluation_corpus,materialize_evaluation_result
from conscious_agent.model_training.training_readiness import assess_training_readiness
from conscious_agent.model_training.model_registry import register_model_candidate
checks=[]
# Readiness target is structurally reachable under default ceilings.
checks.append(sum(DEFAULT_CAPS.values())>=5000)
# Manifest binds exact approved record digests and validates its own digest.
r=create_training_record(task_type='software_development',input_payload='x',model_output='y',validation={'passed':True},capture_authorized=True,created_at_ns=1); s=sanitize_training_record(r); s['approved_for_training']=True; s=_seal({k:v for k,v in s.items() if k!='record_digest'})
m=build_dataset_manifest([s],dataset_version='d1'); checks += [validate_dataset_manifest(m),m['record_bindings'][0]['record_digest']==s['record_digest']]
t=dict(m);t['record_count']=999;checks.append(validate_dataset_manifest(t) is False)
# Corpus digest is verified and duplicate result IDs make evaluation incomplete.
c=freeze_evaluation_corpus([{'case_id':'e1','capability':'governance','prompt':'p','checks':['safe']}],corpus_version='e1');checks.append(validate_evaluation_corpus(c))
cf=dict(c);cf['cases']=[{'case_id':'e1','capability':'governance','prompt':'tampered','checks':['safe']}];checks.append(validate_evaluation_corpus(cf) is False)
dup=score_evaluation_results(c,[{'case_id':'e1','passed':True},{'case_id':'e1','passed':True}],model_id='m');checks += [dup['complete'] is False,dup['duplicate_result_ids'] is True]
# Comparison requires complete baseline and no per-category violation regression.
b={'corpus_digest':c['corpus_digest'],'complete':True,'score':80,'violation_counts':{'authority':0,'citation':2},'model_id':'b'}; cand={'corpus_digest':c['corpus_digest'],'complete':True,'score':90,'violation_counts':{'authority':1,'citation':0},'model_id':'c'};checks.append(compare_model_evaluations(b,cand)['promotion_eligible'] is False)
# Immutable materialized corpus/result/candidate identities reject conflicting overwrites.
with tempfile.TemporaryDirectory() as td:
 a=materialize_evaluation_corpus(runtime_root=td,corpus_version='eval',cases=c['cases'],operator_authorized=True); b2=materialize_evaluation_corpus(runtime_root=td,corpus_version='eval',cases=[{'case_id':'e2','capability':'coding','prompt':'q','checks':[]}],operator_authorized=True);checks += [a['ok'] is True,b2['ok'] is False]
 e=a['corpus']; rr=materialize_evaluation_result(runtime_root=td,corpus=e,results=[{'case_id':'e1','passed':True}],model_id='m',operator_authorized=True); rr2=materialize_evaluation_result(runtime_root=td,corpus=e,results=[{'case_id':'e1','passed':False}],model_id='m',operator_authorized=True);checks += [rr['ok'] is True,rr2['ok'] is False]
 ev=score_evaluation_results(e,[{'case_id':'e1','passed':True}],model_id='eidolon-v1'); mc=register_model_candidate(runtime_root=td,model_id='eidolon-v1',parent_model='base',dataset_manifest_digest='a'*64,training_config_digest='b'*64,artifact_digest='c'*64,evaluation=ev,operator_authorized=True); mc2=register_model_candidate(runtime_root=td,model_id='eidolon-v1',parent_model='base',dataset_manifest_digest='a'*64,training_config_digest='b'*64,artifact_digest='d'*64,evaluation=ev,operator_authorized=True);checks += [mc['ok'] is True,mc2['ok'] is False]
# Readiness requires valid manifests/corpus, not plausible-looking 64-char strings.
fake={'dataset_version':'v1','manifest_digest':'a'*64,'record_count':6000,'capability_counts':{'a':1,'b':1,'c':1,'d':1,'e':1}};base={'complete':True,'corpus_digest':c['corpus_digest']};checks.append(assess_training_readiness(dataset_manifest=fake,evaluation_corpus=c,baseline_evaluation=base)['ready_for_operator_training_review'] is False)
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract':'v2503.4.28.1'}));raise SystemExit(0 if all(checks) else 1)
