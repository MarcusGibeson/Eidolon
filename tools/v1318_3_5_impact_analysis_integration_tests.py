from __future__ import annotations
import sys,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from impact_analysis import *

def fx(base):
 repo=base/'repo';rt=base/'rt';(repo/'pkg').mkdir(parents=True);(repo/'tests').mkdir();(repo/'pkg/__init__.py').write_text('');(repo/'pkg/core.py').write_text('def work(): return 1\n');(repo/'pkg/service.py').write_text('import pkg.core\ndef serve(): return pkg.core.work()\n');(repo/'tests/test_core.py').write_text('from pkg.core import work\ndef test_work(): assert work()==1\n');(repo/'dashboard_ui.py').write_text('import pkg.core\napp.get("/x")\n');(repo/'README_RELEASE_HISTORY.md').write_text('## v1.0 - initial\n');return repo,rt
with tempfile.TemporaryDirectory() as td:
 repo,rt=fx(Path(td));p=build_impact_analysis(repo,['pkg/core.py','missing.py'],runtime_root=rt)['impact_analysis'];req(p['unknown_path_count']==1,'unknown');req(p['candidate_test_count']>=1,'test_candidates');req(not p['tests_executed'],'not_executed');req(process_impact_analysis_control('analyze impact: pkg/core.py',project_root=repo,runtime_root=rt)['active'],'control')
print(json.dumps({'suite':'v1318.3-5-impact-analysis','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
