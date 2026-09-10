from __future__ import annotations
import sys,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from behavioral_map import *

def fx(base):
 repo=base/'repo';rt=base/'rt';(repo/'pkg').mkdir(parents=True);(repo/'tests').mkdir();(repo/'pkg/__init__.py').write_text('');(repo/'pkg/core.py').write_text('def work(): return 1\n');(repo/'pkg/service.py').write_text('import pkg.core\ndef serve(): return pkg.core.work()\n');(repo/'tests/test_core.py').write_text('from pkg.core import work\ndef test_work(): assert work()==1\n');(repo/'dashboard_ui.py').write_text('import pkg.core\napp.get("/x")\n');return repo,rt
with tempfile.TemporaryDirectory() as td:
 repo,rt=fx(Path(td));p=build_behavioral_map(repo,runtime_root=rt)['behavioral_map'];priv=load_behavioral_map(p['workspace_digest'],runtime_root=rt,include_private=True);req(priv['workflows'],'private');req(all(len(x['handler_path_digest'])==64 for x in priv['workflows']),'digests');req(any(x['candidate_test_digests'] for x in priv['workflows']),'test_links')
print(json.dumps({'suite':'v1315.3-5-behavioral-map','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
