from pathlib import Path
import json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT)]
from conscious_agent.model_training.training_record import record_training_interaction,load_training_record
from conscious_agent.model_training.training_sanitizer import sanitize_stored_training_record
from conscious_agent.model_training.training_export import approve_training_record,export_manifest_sft_jsonl,export_manifest_preference_jsonl
from conscious_agent.model_training.training_dataset import build_dataset_manifest,materialize_dataset_manifest,validate_dataset_manifest,_manifest_digest
from conscious_agent.model_training.training_dedup import deduplicate_records
from conscious_agent.model_training.training_eval import freeze_evaluation_corpus,score_evaluation_results,validate_evaluation_corpus,validate_evaluation_result
from conscious_agent.model_training.training_readiness import assess_training_readiness
checks=[]
def ck(v): checks.append(bool(v))
with tempfile.TemporaryDirectory() as td:
    # Failed validation plus a claimed correction must never become approved SFT data.
    r=record_training_interaction(runtime_root=td,capture_authorized=True,task_type='software_repair',input_payload='x',model_output='bad',corrected_output='claimed good',validation={'passed':False,'deterministic':True,'status':'failed'},provenance={'operator_reviewed':True,'difficulty':5,'novelty_score':10})
    rid=r['record']['record_id']; sanitize_stored_training_record(rid,runtime_root=td); denied=approve_training_record(rid,runtime_root=td,operator_approved=True); ck(denied['ok'] is False and denied['status']=='training_record_quality_gate_failed')

    # A verified record can be approved and approval retry is idempotent.
    good=record_training_interaction(runtime_root=td,capture_authorized=True,task_type='software_repair',input_payload='y',model_output='bad',corrected_output='good',validation={'passed':True,'deterministic':True,'tests_passed':True},provenance={'operator_reviewed':True,'difficulty':4})
    gid=good['record']['record_id']; sanitize_stored_training_record(gid,runtime_root=td); a1=approve_training_record(gid,runtime_root=td,operator_approved=True); a2=approve_training_record(gid,runtime_root=td,operator_approved=True); ck(a1['ok'] and a2['ok'] and a2['status']=='training_record_approval_restored')
    manifest=build_dataset_manifest([a1['record']],dataset_version='d1'); ck(validate_dataset_manifest(manifest))

    # Manifest-bound export must honor exact approved record digest and be idempotent.
    ex1=export_manifest_sft_jsonl(runtime_root=td,dataset_manifest=manifest,operator_authorized=True); ex2=export_manifest_sft_jsonl(runtime_root=td,dataset_manifest=manifest,operator_authorized=True); ck(ex1['ok'] and ex2['ok'] and ex1['dataset_manifest_digest']==manifest['manifest_digest'])
    px=export_manifest_preference_jsonl(runtime_root=td,dataset_manifest=manifest,operator_authorized=True); ck(px['ok'] and px['record_count']==1)
    tampered=dict(manifest); tampered['record_bindings']=[dict(manifest['record_bindings'][0],record_digest='f'*64)]; tampered['manifest_digest']=_manifest_digest({k:v for k,v in tampered.items() if k!='manifest_digest'}); bad=export_manifest_sft_jsonl(runtime_root=td,dataset_manifest=tampered,operator_authorized=True); ck(bad['ok'] is False and bad['status']=='training_dataset_record_digest_mismatch')

with tempfile.TemporaryDirectory() as td:
    # Rebuilding an identical dataset version restores instead of conflicting on timestamp.
    m1=materialize_dataset_manifest(runtime_root=td,dataset_version='same',operator_authorized=True); m2=materialize_dataset_manifest(runtime_root=td,dataset_version='same',operator_authorized=True); ck(m1['ok'] and m2['ok'] and m2['status']=='dataset_manifest_restored')

# Semantically invalid but correctly re-hashed manifests are rejected.
fake={'contract_version':'v2503.4.28.2','dataset_version':'fake','record_ids':['trn_same']*5000,'record_bindings':[{'record_id':'trn_same','record_digest':'a'*64}]*5000,'record_count':5000,'capability_counts':{'coding':1000,'research':1000,'planning':1000,'governance':1000,'conversation':1000},'dedup_rejected_count':0,'created_at_ns':1,'runtime_only':True,'model_training_authorized':False,'model_promotion_authorized':False};fake['manifest_digest']=_manifest_digest(fake); ck(validate_dataset_manifest(fake) is False)

cases=[{'case_id':f'e{i}','capability':'coding','prompt':'p','checks':[]} for i in range(500)]; corpus=freeze_evaluation_corpus(cases,corpus_version='holdout'); results=[{'case_id':f'e{i}','passed':True} for i in range(500)]; baseline=score_evaluation_results(corpus,results,model_id='base'); ck(validate_evaluation_corpus(corpus) and validate_evaluation_result(baseline,corpus=corpus))
# Self-rehashed corpus with duplicate case ids must fail semantic validation.
forged_corpus=dict(corpus); forged_corpus['cases']=list(corpus['cases']); forged_corpus['cases'][1]=dict(forged_corpus['cases'][0]); forged_corpus['corpus_digest']=__import__('hashlib').sha256(json.dumps({'corpus_version':forged_corpus['corpus_version'],'cases':forged_corpus['cases']},ensure_ascii=True,sort_keys=True,separators=(',',':')).encode()).hexdigest(); ck(validate_evaluation_corpus(forged_corpus) is False)
# Baseline receipt tampering must fail readiness even if 'complete' remains true.
bindings=[]; ids=[]
for cap in ("coding","research","planning","governance","conversation"):
    for i in range(1000):
        rid=f"trn_{cap}_{i}"; ids.append(rid); bindings.append({"record_id":rid,"record_digest":__import__("hashlib").sha256(rid.encode()).hexdigest()})
manifest2={"contract_version":"v2503.4.28.2","dataset_version":"big","record_ids":ids,"record_bindings":bindings,"record_count":5000,"capability_counts":{"coding":1000,"research":1000,"planning":1000,"governance":1000,"conversation":1000},"dedup_rejected_count":0,"created_at_ns":1,"runtime_only":True,"model_training_authorized":False,"model_promotion_authorized":False}; manifest2["manifest_digest"]=_manifest_digest(manifest2)
ready=assess_training_readiness(dataset_manifest=manifest2,evaluation_corpus=corpus,baseline_evaluation=baseline); ck(ready["ready_for_operator_training_review"] is True)
tampered_eval=dict(baseline); tampered_eval['score']=99.0; ck(assess_training_readiness(dataset_manifest=manifest2,evaluation_corpus=corpus,baseline_evaluation=tampered_eval)['ready_for_operator_training_review'] is False)


# Readiness-scale distinct corpora must no longer trigger all-pairs near-duplicate work.
scale=[]
for i in range(5000):
    cap=("coding","repair","research","planning","governance")[i%5]
    scale.append({"record_id":f"trn_scale_{i}","task_type":"other","input_payload":f"unique task {i} alpha beta","model_output":f"unique result {i} gamma delta","validation":{"passed":True},"validation_passed":True,"provenance":{"capability":cap},"sanitized":True,"approved_for_training":True})
scale_out=deduplicate_records(scale); ck(scale_out["kept_count"]==5000 and not scale_out["rejected"])
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract':'v2503.4.28.2'})); raise SystemExit(0 if all(checks) else 1)
