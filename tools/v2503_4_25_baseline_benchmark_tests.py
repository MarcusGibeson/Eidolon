from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT)]
from conscious_agent.model_training.training_eval import freeze_evaluation_corpus,score_evaluation_results
c=freeze_evaluation_corpus([{'case_id':'a','capability':'coding','prompt':'p','checks':['x']},{'case_id':'b','capability':'governance','prompt':'q','checks':['y']}],corpus_version='v1'); r=score_evaluation_results(c,[{'case_id':'a','passed':True,'latency_ms':100},{'case_id':'b','passed':False,'latency_ms':300,'violations':['authority']}],model_id='base'); checks=[r['passed']==1,r['total']==2,r['score']==50.0,r['violation_counts']['authority']==1,r['mean_latency_ms']==200.0,r['complete'] is True,r['model_training_authorized'] is False]
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract':'v2503.4.25'}));raise SystemExit(0 if all(checks) else 1)
