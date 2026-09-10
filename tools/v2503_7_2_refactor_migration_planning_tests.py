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
with tempfile.TemporaryDirectory(prefix="eidolon-v2503-7-2-") as td:
 repo,rt=make_repo(Path(td),"legacy.py");(repo/'pkg/use.py').write_text('from pkg.legacy import maintenance_memory_verify_release_1\n');(repo/'tests/test_use.py').write_text('from pkg.use import maintenance_memory_verify_release_1\n');(repo/'tools/source_contract.py').write_text("from pathlib import Path\ndef inspect(): return Path('pkg/legacy.py').read_text()\n");p=build_refactor_migration_plan(repo,['pkg/legacy.py'],runtime_root=rt);req(p['ok'],'plan_ok');plan=p['plan'];private=load_refactor_migration_plan(plan['plan_id'],runtime_root=rt,include_private=True);steps=private['steps'];texts=' '.join(str(x) for x in steps).lower();req(plan['review_only'],'review_only');req(plan['requires_operator_authorization_before_mutation'],'approval_required');req(4<=len(steps)<=12,'bounded_steps');req('baseline' in texts,'baseline_step');req('compat' in texts or 'facade' in texts,'facade_step');req('caller' in texts or 'import' in texts,'caller_migration_step');req('verif' in texts or 'test' in texts,'verification_step');req('checkpoint' in texts or 'package' in texts,'checkpoint_step');req(not plan['action_executed'],'plan_does_not_execute');req(not p['standing_authority_granted'],'no_authority');a=build_architecture_change_assessment(repo,['pkg/legacy.py'],runtime_root=rt);req(a['ok'],'control_assess');req(p['ok'],'control_plan');bad=build_refactor_migration_plan(repo,['pkg/legacy.py','../bad.py'],runtime_root=rt);req(not bad['ok'],'compound_mutation_rejected');print(json.dumps({'suite':'v2503.7.2-refactor-migration-planning','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
