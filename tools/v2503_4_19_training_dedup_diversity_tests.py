from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT)]
from conscious_agent.model_training.training_record import create_training_record
from conscious_agent.model_training.training_dedup import deduplicate_records,similarity

def rec(i,text,task='conversation'):
 return create_training_record(task_type=task,input_payload=text,model_output='answer '+text,validation={'passed':True},capture_authorized=True,created_at_ns=i)
a=rec(1,'same task'); b=rec(2,'same task'); c=rec(3,'different unrelated words', 'research_synthesis'); out=deduplicate_records([a,b,c]); checks=[out['kept_count']==2,len(out['rejected'])==1,out['rejected'][0]['reason'] in {'exact_duplicate','near_duplicate'},out['capability_counts']['conversation']==1,out['capability_counts']['research']==1,similarity(a,b)>.9,similarity(a,c)==0,out['model_training_authorized'] is False]
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract':'v2503.4.19'}));raise SystemExit(0 if all(checks) else 1)
