import json, os, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['PYTHONDONTWRITEBYTECODE']='1'; os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp()
from conscious_agent.architecture_checkpoint_dispatch import build_checkpoint_dispatch_consolidation, dispatch_registered_checkpoint
r=build_checkpoint_dispatch_consolidation(source_root=ROOT, runtime_root=os.environ['EIDOLON_DATA_DIR'], invoke_checkpoint_ids=('conversation-cognition-unification','understandable-cognitive-controls')); checks=[r['contract_version']=='v1150.2',r['descriptor_count']>=150,r['requested_dispatch_count']==2,r['all_requested_checkpoints_read_only'],r['historical_aliases_preserved'],not r['raw_checkpoint_content_included'],not r['provider_contacted'] and not r['runtime_mutated']]
one=dispatch_registered_checkpoint('conversation-cognition-unification',source_root=ROOT,runtime_root=os.environ['EIDOLON_DATA_DIR']); checks += [one['checkpoint_summary']['invocation_supported'],one['checkpoint_summary']['reported_read_only'] and not one['checkpoint_summary']['post_available'],not one['raw_checkpoint_included']]
try: dispatch_registered_checkpoint('missing',source_root=ROOT); checks.append(False)
except KeyError: checks.append(True)
assert all(checks); print(json.dumps({'suite':'v1147.3-compatibility','passed':len(checks),'total':len(checks)}))
