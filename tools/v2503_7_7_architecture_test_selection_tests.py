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
with tempfile.TemporaryDirectory(prefix='eidolon-v2503-7-7-') as td:
 repo,rt=make_repo(Path(td));(repo/'helpers').mkdir();(repo/'helpers/__init__.py').write_text('');(repo/'pkg/core.py').write_text('def work(): return 1\n');(repo/'pkg/direct.py').write_text('from pkg.core import work\n');(repo/'tests/test_direct.py').write_text('from pkg.core import work\ndef test_x(): assert work()==1\n');(repo/'helpers/source_shape.py').write_text("from pathlib import Path\ndef inspect(): return Path('pkg/core.py').read_text()\n");(repo/'tests/test_shape.py').write_text('from helpers.source_shape import inspect\ndef test_shape(): assert "work" in inspect()\n');r=build_architecture_change_assessment(repo,['pkg/core.py'],runtime_root=rt);p=load_architecture_change_assessment(r['assessment']['analysis_id'],runtime_root=rt,include_private=True);f=p['findings'][0];req('tests/test_direct.py' in f['candidate_tests'],'direct_test_selected');req('tests/test_shape.py' in f['candidate_tests'],'structural_helper_test_selected');rows={x['path']:x for x in f['test_candidates']};req('direct_importer' in rows['tests/test_direct.py']['reasons'],'direct_reason');req('consumer_dependency' in rows['tests/test_shape.py']['reasons'],'consumer_reason');req(rows['tests/test_shape.py']['priority']<=3,'priority_bounded');req(f['candidate_test_count']==2,'exact_test_count');pub=r['assessment']['target_summaries'][0];req(pub['test_candidate_reason_counts'].get('direct_importer',0)>=1,'public_reason_counts');req(pub['test_candidate_reason_counts'].get('consumer_dependency',0)>=1,'public_consumer_count');print(json.dumps({'suite':'v2503.7.7-architecture-test-selection','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
