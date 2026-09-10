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
from architecture_change_reasoning import *
from architecture_project_goal import *
with tempfile.TemporaryDirectory(prefix='eidolon-v2503-7-6-') as td:
 repo,rt=make_repo(Path(td));(repo/'tools/mention.py').write_text("NOTE='giant.py'\n");(repo/'tools/inspect.py').write_text("from pathlib import Path\ndef inspect(): return Path('pkg/giant.py').read_text()\n");a=build_architecture_change_assessment(repo,['pkg/giant.py'],runtime_root=rt);p=load_architecture_change_assessment(a['assessment']['analysis_id'],runtime_root=rt,include_private=True);f=p['findings'][0];req(f['filename_reference_count']>=2,'mentions_counted');req(f['filename_bound_consumer_count']==1,'structural_consumer_precise');req('tools/inspect.py' in f['filename_bound_consumers'],'structural_consumer_identified');req('tools/mention.py' not in f['filename_bound_consumers'],'mere_mention_not_binding');d=discover_architecture_goal_candidates(repo,runtime_root=rt);c=d['candidates'][0];req(c['filename_bound_consumer_count']==1,'candidate_uses_structural_count');g=prepare_architecture_project_goal(repo,c['candidate_id'],runtime_root=rt);req(g['ok'],'fresh_candidate_prepares');d2=discover_architecture_goal_candidates(repo,runtime_root=rt);c2=d2['candidates'][0];(repo/'pkg/giant.py').write_text((repo/'pkg/giant.py').read_text()+'\n# changed\n');stale=prepare_architecture_project_goal(repo,c2['candidate_id'],runtime_root=rt);req(not stale['ok'] and stale['status']=='architecture_goal_candidate_stale','stale_candidate_rejected');print(json.dumps({'suite':'v2503.7.6-architecture-evidence-precision','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
