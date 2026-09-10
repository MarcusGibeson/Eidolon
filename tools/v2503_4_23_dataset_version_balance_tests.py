from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT)]
from conscious_agent.model_training.training_record import create_training_record
from conscious_agent.model_training.training_dataset import build_dataset_manifest
rs=[]
for i,task in enumerate(['conversation','conversation','research_synthesis','planning','tool_use']): rs.append(create_training_record(task_type=task,input_payload=f'{task}-{i}',model_output=f'o{i}',validation={'passed':True},capture_authorized=True,created_at_ns=i+1))
m=build_dataset_manifest(rs,dataset_version='eidolon-training-v1',per_capability_caps={'conversation':1}); checks=[m['dataset_version']=='eidolon-training-v1',m['record_count']==4,m['capability_counts']['conversation']==1,len(m['manifest_digest'])==64,m['runtime_only'] is True,m['model_training_authorized'] is False]
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract':'v2503.4.23'}));raise SystemExit(0 if all(checks) else 1)
