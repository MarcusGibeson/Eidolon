import hashlib,json,tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT)]

from conscious_agent.model_training.training_record import record_training_interaction
from conscious_agent.model_training.training_sanitizer import sanitize_stored_training_record
from conscious_agent.model_training.training_export import approve_training_record
from conscious_agent.model_training.training_dataset import materialize_dataset_manifest
from conscious_agent.model_training.training_provenance import materialize_dataset_provenance,validate_dataset_provenance,validate_dataset_provenance_against_store
from conscious_agent.model_training.training_eval import freeze_evaluation_corpus
from conscious_agent.model_training.training_benchmark import run_frozen_corpus
from conscious_agent.model_training.training_readiness import assess_training_readiness
from conscious_agent.model_training.model_registry import register_model_candidate
checks=[]
def ck(x): checks.append(bool(x))
def digest(v): return hashlib.sha256(json.dumps(v,ensure_ascii=True,sort_keys=True,separators=(',',':')).encode()).hexdigest()
with tempfile.TemporaryDirectory() as td:
    root=Path(td); caps=['software_development','research_synthesis','planning','governance','conversation']
    for i,cap in enumerate(caps):
        raw=record_training_interaction(runtime_root=root,capture_authorized=True,task_type=cap,input_payload=f'x{i}',model_output=f'y{i}',validation={'passed':True,'tests_passed':True})
        sanitize_stored_training_record(raw['record']['record_id'],runtime_root=root); ck(approve_training_record(raw['record']['record_id'],runtime_root=root,operator_approved=True)['ok'])
    m=materialize_dataset_manifest(runtime_root=root,dataset_version='audit',operator_authorized=True); ck(m['ok'])
    p=materialize_dataset_provenance(runtime_root=root,manifest=m['manifest'],operator_authorized=True); ck(p['ok']); ck(validate_dataset_provenance_against_store(p['certificate'],manifest=m['manifest'],runtime_root=root))
    # A portable self-hashed forgery must not be sufficient for readiness.
    forged=dict(p['certificate']); forged['approved_record_bindings_digest']='0'*64; forged['certificate_digest']=digest({k:v for k,v in forged.items() if k!='certificate_digest'})
    ck(validate_dataset_provenance(forged,manifest=m['manifest']))
    ck(not validate_dataset_provenance_against_store(forged,manifest=m['manifest'],runtime_root=root))
    corpus=freeze_evaluation_corpus([{'case_id':'e1','capability':'coding','prompt':'p','checks':[]}],corpus_version='e1')
    b=run_frozen_corpus(corpus=corpus,model_id='base',provider_generate=lambda p:'ok',operator_authorized=True); ck(b['provider_request_count']==1)
    calls=[]
    def boom(p): calls.append(p); raise RuntimeError('x')
    failed=run_frozen_corpus(corpus=corpus,model_id='base',provider_generate=boom,operator_authorized=True); ck(failed['provider_contacted'] is True and failed['provider_request_count']==1)
    ck(run_frozen_corpus(corpus=corpus,model_id='',provider_generate=lambda p:'ok',operator_authorized=True)['status']=='benchmark_model_id_required')
    ready=assess_training_readiness(dataset_manifest=m['manifest'],dataset_provenance=p['certificate'],runtime_root=root,evaluation_corpus=corpus,baseline_evaluation=b['evaluation'],minimum_records=1,minimum_eval_cases=1); ck(ready['ready_for_operator_training_review'])

    valid_digest='a'*64
    reg=register_model_candidate(runtime_root=root,model_id='base',parent_model='parent',dataset_manifest_digest=valid_digest,training_config_digest='b'*64,artifact_digest='c'*64,evaluation=b['evaluation'],operator_authorized=True); ck(reg['ok'])
    ck(register_model_candidate(runtime_root=root,model_id='base2',parent_model='parent',dataset_manifest_digest='z'*64,training_config_digest='b'*64,artifact_digest='c'*64,evaluation=b['evaluation'],operator_authorized=True)['status']=='model_candidate_digest_invalid')
    ck(register_model_candidate(runtime_root=root,model_id='other',parent_model='parent',dataset_manifest_digest=valid_digest,training_config_digest='b'*64,artifact_digest='c'*64,evaluation=b['evaluation'],operator_authorized=True)['status']=='model_candidate_evaluation_invalid')
    fake=assess_training_readiness(dataset_manifest=m['manifest'],dataset_provenance=forged,runtime_root=root,evaluation_corpus=corpus,baseline_evaluation=b['evaluation'],minimum_records=1,minimum_eval_cases=1); ck(not fake['ready_for_operator_training_review'])
print(json.dumps({'suite':'v2503.4.30.1-training-provenance-benchmark-audit','ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True))
assert all(checks)
