from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT)]
from conscious_agent.model_training.training_readiness import assess_training_readiness
from conscious_agent.model_training.training_dataset import _manifest_digest
from conscious_agent.model_training.training_eval import freeze_evaluation_corpus,score_evaluation_results
bindings=[{'record_id':f'trn_{i:024d}','record_digest':'a'*64} for i in range(6000)]
d={'contract_version':'v2503.4.28.1','dataset_version':'v1','record_ids':[x['record_id'] for x in bindings],'record_bindings':bindings,'record_count':6000,'capability_counts':{'coding':1200,'research':1200,'planning':1200,'governance':1200,'conversation':1200},'dedup_rejected_count':0,'created_at_ns':1,'runtime_only':True,'model_training_authorized':False,'model_promotion_authorized':False};d['manifest_digest']=_manifest_digest(d)
cases=[{'case_id':f'e{i}','capability':'coding','prompt':'p','checks':[]} for i in range(600)];e=freeze_evaluation_corpus(cases,corpus_version='e1');b=score_evaluation_results(e,[{'case_id':f'e{i}','passed':True} for i in range(600)],model_id='base');ok=assess_training_readiness(dataset_manifest=d,evaluation_corpus=e,baseline_evaluation=b); no=assess_training_readiness(dataset_manifest={**d,'record_count':100},evaluation_corpus=e,baseline_evaluation=b);checks=[ok['ready_for_operator_training_review'] is True,ok['automatic_training'] is False,ok['model_training_authorized'] is False,ok['model_promotion_authorized'] is False,no['ready_for_operator_training_review'] is False,'dataset_large_enough' in no['missing']]
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract':'v2503.4.28'}));raise SystemExit(0 if all(checks) else 1)
