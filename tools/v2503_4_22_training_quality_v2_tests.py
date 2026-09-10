from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT)]
from conscious_agent.model_training.training_record import create_training_record
from conscious_agent.model_training.training_sanitizer import sanitize_training_record
from conscious_agent.model_training.training_quality import assess_training_record_quality
r=create_training_record(task_type='software_repair',input_payload='x',model_output='bad',corrected_output='good',validation={'passed':True,'tests_passed':True},provenance={'difficulty':5,'novelty_score':10,'operator_reviewed':True},capture_authorized=True,created_at_ns=1); q=assess_training_record_quality(sanitize_training_record(r)); checks=[q['eligible_for_operator_approval'] is True,q['quality_score']>=90,q['difficulty']==5,q['novelty_score']==10,'difficulty_5' in q['reasons'],q['automatic_approval'] is False,q['model_training_authorized'] is False]
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract':'v2503.4.22'}));raise SystemExit(0 if all(checks) else 1)
