from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT)]
from conscious_agent.model_training.training_eval import compare_model_evaluations
b={'model_id':'base','corpus_digest':'a'*64,'score':80,'violation_counts':{'authority':2},'complete':True}; c={'model_id':'candidate','corpus_digest':'a'*64,'score':87,'violation_counts':{'authority':1},'complete':True}; out=compare_model_evaluations(b,c); checks=[out['ok'] is True,out['score_delta']==7.0,out['violation_delta']==-1,out['promotion_eligible'] is True,out['operator_approval_required'] is True,out['model_promotion_authorized'] is False,compare_model_evaluations(b,{**c,'corpus_digest':'b'*64})['ok'] is False]
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract':'v2503.4.26'}));raise SystemExit(0 if all(checks) else 1)
