from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT)]
from conscious_agent.model_training.training_eval import freeze_evaluation_corpus
cases=[{'case_id':'e1','capability':'research','prompt':'p','checks':['citation']},{'case_id':'e2','capability':'governance','prompt':'q','checks':['no_authority']}]; c=freeze_evaluation_corpus(cases,corpus_version='eval-v1'); checks=[c['frozen'] is True,c['case_count']==2,len(c['corpus_digest'])==64,c['model_training_authorized'] is False];
try: freeze_evaluation_corpus([cases[0],cases[0]],corpus_version='bad'); checks.append(False)
except ValueError: checks.append(True)
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract':'v2503.4.24'}));raise SystemExit(0 if all(checks) else 1)
