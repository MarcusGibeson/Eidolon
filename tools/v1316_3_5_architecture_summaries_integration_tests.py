from __future__ import annotations
import sys,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from architecture_summaries import *

def fx(base):
 repo=base/'repo';rt=base/'rt';(repo/'pkg').mkdir(parents=True);(repo/'tests').mkdir();(repo/'pkg/__init__.py').write_text('');(repo/'pkg/core.py').write_text('def work(): return 1\n');(repo/'pkg/service.py').write_text('import pkg.core\ndef serve(): return pkg.core.work()\n');(repo/'tests/test_core.py').write_text('from pkg.core import work\ndef test_work(): assert work()==1\n');(repo/'dashboard_ui.py').write_text('import pkg.core\napp.get("/x")\n');(repo/'README_RELEASE_HISTORY.md').write_text('## v1.0 - initial\n');return repo,rt
with tempfile.TemporaryDirectory() as td:
 repo,rt=fx(Path(td));p=build_architecture_summaries(repo,runtime_root=rt)['architecture_summaries'];priv=load_architecture_summaries(p['workspace_digest'],runtime_root=rt,include_private=True);req(len(priv['summaries'])==5,'private_summaries');req(all(x['content_free'] for x in priv['summaries']),'content_free');c=process_architecture_summary_control('show architecture summary',project_root=repo,runtime_root=rt);req(c['active'] and c['ok'],'control')
print(json.dumps({'suite':'v1316.3-5-architecture-summaries','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
