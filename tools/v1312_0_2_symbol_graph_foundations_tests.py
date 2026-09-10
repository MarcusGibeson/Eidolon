from __future__ import annotations
import sys,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from symbol_graph import *

def fx(base):
 repo=base/'repo';rt=base/'rt';(repo/'pkg').mkdir(parents=True);(repo/'tests').mkdir();(repo/'pkg/__init__.py').write_text('');(repo/'pkg/core.py').write_text('def work(): return 1\n');(repo/'pkg/service.py').write_text('import pkg.core\ndef serve(): return pkg.core.work()\n');(repo/'tests/test_core.py').write_text('from pkg.core import work\ndef test_work(): assert work()==1\n');(repo/'dashboard_ui.py').write_text('import pkg.core\napp.get("/x")\n');return repo,rt
with tempfile.TemporaryDirectory() as td:
 repo,rt=fx(Path(td));p=build_symbol_graph(repo,runtime_root=rt)['symbol_graph'];req(p['symbol_count']>=4,'symbols');req(p['edge_count']>=3,'edges');req(p['coverage_candidate_count']>=1,'coverage_candidate');req(not p['measured_test_coverage'],'not_coverage')
print(json.dumps({'suite':'v1312.0-2-symbol-graph','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
