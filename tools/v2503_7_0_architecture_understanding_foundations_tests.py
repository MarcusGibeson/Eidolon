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
from architecture_change_reasoning import build_architecture_change_assessment,load_architecture_change_assessment
with tempfile.TemporaryDirectory(prefix="eidolon-v2503-7-0-") as td:
 repo,rt=make_repo(Path(td));(repo/'pkg/helper.py').write_text('from pkg.giant import maintenance_memory_verify_release_1\n');(repo/'tests/test_helper.py').write_text('from pkg.helper import maintenance_memory_verify_release_1\n');(repo/'tools/source_contract.py').write_text("from pathlib import Path\ndef inspect(): return Path('pkg/giant.py').read_text()\n")
 before=(repo/'pkg/giant.py').read_bytes();r=build_architecture_change_assessment(repo,['pkg/giant.py'],runtime_root=rt);req(r['ok'],'assessment_ok');req(r['assessment']['contract_version']=='v2503.7.2','contract');p=load_architecture_change_assessment(r['assessment']['analysis_id'],runtime_root=rt,include_private=True);f=p['findings'][0];req(f['target_path']=='pkg/giant.py','known_target');req('tests/test_helper.py' in f['transitive_importers'],'transitive_impact');req('tests/test_helper.py' in f['candidate_tests'],'test_candidate');req('tools/source_contract.py' in f['filename_bound_consumers'],'filename_contract');req(any(x['responsibility']=='memory' for x in f['responsibilities']),'responsibility_memory');req(bool(f['suggested_owner']),'suggested_owner');req(f['compatibility_facade_recommended'],'facade_required');req(f['risk'] in {'high','very_high'},'risk_classified');req(not r['assessment'].get('source_paths_exposed',False),'truth_privacy');req(not r['action_executed'] and not r['standing_authority_granted'],'authority_denied');req((repo/'pkg/giant.py').read_bytes()==before,'source_immutable');u=build_architecture_change_assessment(repo,['pkg/missing.py'],runtime_root=rt);req(not u['ok'],'unknown_rejected');req(u['assessment'].get('unknown_path_count',0)>=1,'unknown_count');bad=build_architecture_change_assessment(repo,['../escape.py'],runtime_root=rt);req(not bad['ok'],'invalid_rejected');req(bad['assessment'].get('invalid_path_count',0)>=1,'invalid_count');print(json.dumps({'suite':'v2503.7.0-architecture-understanding-foundations','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
