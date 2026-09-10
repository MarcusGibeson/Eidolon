from __future__ import annotations
import json,sys,tempfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n): checks.append(n); assert v,n
def make_repo(base, giant_name="giant.py"):
 repo=base/'repo';rt=base/'rt';(repo/'pkg').mkdir(parents=True);(repo/'tools').mkdir();(repo/'tests').mkdir();(repo/'pkg/__init__.py').write_text('')
 lines=[]
 for i in range(220): lines += [f'def maintenance_memory_verify_release_{i}(x):','    return x','','']
 (repo/f'pkg/{giant_name}').write_text('\n'.join(lines))
 return repo,rt
from architecture_project_goal import discover_architecture_goal_candidates
with tempfile.TemporaryDirectory(prefix="eidolon-v2503-7-3-") as td:
 repo,rt=make_repo(Path(td));(repo/'tools/source_shape.py').write_text("from pathlib import Path\ndef inspect(): return Path('pkg/giant.py').read_text()\n");d=discover_architecture_goal_candidates(repo,runtime_root=rt);req(d['ok'],'discovery_ok');req(d['candidate_count']>=1,'candidate_found');c=d['candidates'][0];req(not c['auto_selected'],'not_selected');req(not c['goal_activated'],'not_activated');req(not d['action_executed'],'no_action');req(c['candidate_only'],'candidate_only');req(len(c['architecture_reasons'])>=2,'evidence_reasons');req(c['responsibility_count']>=4,'mixed_responsibilities');req(c['filename_bound_consumer_count']>=1,'filename_contract_seen');req(not d['automatic_selection_performed'],'candidate_inert');print(json.dumps({'suite':'v2503.7.3-architecture-hotspot-discovery','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
