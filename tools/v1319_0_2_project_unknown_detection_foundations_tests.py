from __future__ import annotations
import sys,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from project_unknown_detection import *

def fx(base):
 repo=base/'repo';rt=base/'rt';(repo/'pkg').mkdir(parents=True);(repo/'tests').mkdir();(repo/'pkg/__init__.py').write_text('');(repo/'pkg/core.py').write_text('def work(): return 1\n');(repo/'pkg/service.py').write_text('import pkg.core\ndef serve(): return pkg.core.work()\n');(repo/'tests/test_core.py').write_text('from pkg.core import work\ndef test_work(): assert work()==1\n');(repo/'dashboard_ui.py').write_text('import pkg.core\napp.get("/x")\n');(repo/'README_RELEASE_HISTORY.md').write_text('## v1.0 - initial\n');return repo,rt
a=make_claim('x','assumed',[],0.9);req(CONTRACT_VERSION=='v1319.8','contract');req(a['confidence']<=CAP['assumed'],'cap');req(not a['unknown_is_false'],'unknown_not_false');req(set(STATES)>={'observed','inferred','unverified','stale','contradicted'},'states')
print(json.dumps({'suite':'v1319.0-2-project-unknowns','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
