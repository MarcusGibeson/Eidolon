import tempfile
from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT)]

from conscious_agent.model_training.training_record import record_training_interaction
from conscious_agent.model_training.training_sanitizer import sanitize_stored_training_record
from conscious_agent.model_training.training_export import approve_training_record
from conscious_agent.model_training.training_dataset import materialize_dataset_manifest
from conscious_agent.model_training.training_provenance import materialize_dataset_provenance,validate_dataset_provenance
from conscious_agent.model_training.training_eval import freeze_evaluation_corpus
from conscious_agent.model_training.training_benchmark import run_frozen_corpus
from conscious_agent.model_training.training_readiness import assess_training_readiness
checks=[]
def ck(x): checks.append(bool(x))
with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    caps=['software_development','research_synthesis','planning','governance','conversation']
    for i in range(5):
        raw=record_training_interaction(runtime_root=root,capture_authorized=True,task_type=caps[i],input_payload=f'fix {i}',model_output=f'answer {i}',validation={'passed':True,'tests_passed':True})
        clean=sanitize_stored_training_record(raw['record']['record_id'],runtime_root=root)
        a=approve_training_record(raw['record']['record_id'],runtime_root=root,operator_approved=True)
        ck(a['ok'])
    m=materialize_dataset_manifest(runtime_root=root,dataset_version='v1',operator_authorized=True)
    ck(m['ok'])
    p=materialize_dataset_provenance(runtime_root=root,manifest=m['manifest'],operator_authorized=True)
    ck(p['ok'] and validate_dataset_provenance(p['certificate'],manifest=m['manifest']))
    bad=dict(p['certificate']);bad['record_count']=99
    ck(not validate_dataset_provenance(bad,manifest=m['manifest']))
    corpus=freeze_evaluation_corpus([{'case_id':'e1','capability':'coding','prompt':'hello','checks':[]}],corpus_version='e1')
    b=run_frozen_corpus(corpus=corpus,model_id='stub',provider_generate=lambda q:'ok',operator_authorized=True,check_runner=lambda case,out:{'passed':out=='ok','violations':[]})
    ck(b['ok'] and b['provider_request_count']==1 and b['raw_model_outputs_returned'] is False)
    ck(run_frozen_corpus(corpus=corpus,model_id='stub',provider_generate=lambda q:'ok',operator_authorized=False)['provider_contacted'] is False)
    readiness=assess_training_readiness(dataset_manifest=m['manifest'],dataset_provenance=p['certificate'],runtime_root=root,evaluation_corpus=corpus,baseline_evaluation=b['evaluation'],minimum_records=1,minimum_eval_cases=1)
    ck(readiness['ready_for_operator_training_review'] is True)
    no=assess_training_readiness(dataset_manifest=m['manifest'],evaluation_corpus=corpus,baseline_evaluation=b['evaluation'],minimum_records=1,minimum_eval_cases=1)
    ck(no['ready_for_operator_training_review'] is False and 'dataset_approved_store_provenance' in no['missing'])
print(json.dumps({'suite':'v2503.4.30-training-provenance-benchmark','ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True))
assert all(checks)
