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
with tempfile.TemporaryDirectory(prefix="eidolon-v2503-7-1-") as td:
 repo,rt=make_repo(Path(td));(repo/'pkg/sub').mkdir();(repo/'pkg/sub/__init__.py').write_text('');(repo/'pkg/sub/consumer.py').write_text('from ..giant import maintenance_memory_verify_release_1\n');(repo/'pkg/top.py').write_text('from pkg.sub.consumer import maintenance_memory_verify_release_1\n');(repo/'tests/test_top.py').write_text('from pkg.top import maintenance_memory_verify_release_1\n');r=build_architecture_change_assessment(repo,['pkg/giant.py'],runtime_root=rt);p=load_architecture_change_assessment(r['assessment']['analysis_id'],runtime_root=rt,include_private=True);f=p['findings'][0];req('pkg/sub/consumer.py' in f['direct_importers'],'relative_import_resolved');req('pkg/top.py' in f['transitive_importers'],'transitive_resolved');req('tests/test_top.py' in f['transitive_importers'],'test_transitive_resolved');req('tests/test_top.py' in f['candidate_tests'],'candidate_test');req(bool(f['recommended_strategy']),'strategy_present');req(f['predictions_not_proof'],'epistemic_boundary');req(not r['action_executed'],'no_execution');print(json.dumps({'suite':'v2503.7.1-change-impact-reasoning','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
