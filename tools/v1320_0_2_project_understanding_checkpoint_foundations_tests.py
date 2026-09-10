from __future__ import annotations
import sys,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from project_understanding_checkpoint import *

def fx(base):
 repo=base/'repo';rt=base/'rt';(repo/'pkg').mkdir(parents=True);(repo/'tests').mkdir();(repo/'pkg/__init__.py').write_text('');(repo/'pkg/core.py').write_text('def work(): return 1\n');(repo/'pkg/service.py').write_text('import pkg.core\ndef serve(): return pkg.core.work()\n');(repo/'tests/test_core.py').write_text('from pkg.core import work\ndef test_work(): assert work()==1\n');(repo/'dashboard_ui.py').write_text('import pkg.core\napp.get("/x")\n');(repo/'README_RELEASE_HISTORY.md').write_text('## v1.0 - initial\n');return repo,rt
with tempfile.TemporaryDirectory() as td:
 repo,rt=fx(Path(td));p=build_project_understanding_checkpoint(repo,changed_paths=['pkg/core.py'],runtime_root=rt)['project_understanding'];req(CONTRACT_VERSION=='v1320.8','contract');req(p['layer_count']==9,'nine_layers');req(p['manifest_consistent'],'manifest');req(p['unfamiliar_project_supported'],'unfamiliar')
print(json.dumps({'suite':'v1320.0-2-project-understanding','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
