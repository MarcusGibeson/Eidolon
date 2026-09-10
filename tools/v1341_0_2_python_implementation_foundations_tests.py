from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1341_python_implementation_test_support import *
from python_implementation import *

def main():
 p=[0]
 def req(x,n): assert x,n; p[0]+=1
 req(REQUIRED_PRECONDITIONS==('git','file_read','file_patch','shell'),'python_preconditions_explicit')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));summary=inspect_python_project(src)
  req(summary['inspection_only'] and not summary['network_contacted'] and not summary['dependency_installed'],'inspection_has_no_side_effects')
  req(summary['python_file_count']>=3 and summary['test_file_count']>=1 and summary['syntax_invalid_file_count']==0,'project_shape_detected')
  req(summary['async_public_function_count']>=1 and summary['fully_annotated_public_function_count']>=2,'typing_and_async_detected')
  bad=implementation_args(src,runtime,grant,{k:v for k,v in pres.items() if k!='shell'},git);r=run_python_implementation(**bad);req(not r['ok'] and r['status']=='complete_python_preconditions_required' and not r['action_executed'] and not r['release_authorized'],'missing_precondition_blocks_execution')
 print({'ok':True,'suite':'v1341.0-2-python-implementation-foundations','passed':p[0],'total':5})
if __name__=='__main__': main()
