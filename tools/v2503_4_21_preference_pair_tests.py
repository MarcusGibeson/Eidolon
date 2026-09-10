from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT)]
from conscious_agent.model_training.training_record import create_training_record
from conscious_agent.model_training.training_sanitizer import sanitize_training_record
from conscious_agent.model_training.training_preferences import build_preference_pair
base=create_training_record(task_type='software_repair',input_payload='fix',model_output='bad',corrected_output='good',validation={'passed':True},capture_authorized=True,created_at_ns=1); clean=sanitize_training_record(base); pair=build_preference_pair(clean); no=sanitize_training_record(create_training_record(task_type='conversation',input_payload='x',model_output='y',validation={'passed':True},capture_authorized=True,created_at_ns=2)); checks=[pair['ok'] is True,pair['chosen']=='good',pair['rejected']=='bad',pair['capability']=='repair',build_preference_pair(base)['ok'] is False,build_preference_pair(no)['status']=='preference_pair_unavailable',pair['model_training_authorized'] is False]
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract':'v2503.4.21'}));raise SystemExit(0 if all(checks) else 1)
