from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT)]
from conscious_agent.model_training.training_record import create_training_record
from conscious_agent.model_training.training_schema import normalize_training_record
r=create_training_record(task_type='software_repair',input_payload={'x':'fix'},model_output='bad',validation={'passed':True,'tests_passed':True},corrected_output='good',provenance={'difficulty':4},capture_authorized=True,created_at_ns=1)
n=normalize_training_record(r); c=[n['schema_version']=='2',n['capability']=='repair',n['chosen_output']=='good',n['rejected_output']=='bad',n['has_preference_pair'] is True,n['difficulty']==4,len(n['semantic_fingerprint'])==64,len(n['normalized_digest'])==64,n['model_training_authorized'] is False]
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c),'contract':'v2503.4.18'}));raise SystemExit(0 if all(c) else 1)
