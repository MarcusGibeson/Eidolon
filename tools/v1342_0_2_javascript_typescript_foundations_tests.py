from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1342_javascript_typescript_test_support import *
from javascript_typescript_implementation import *
def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 req(REQUIRED_PRECONDITIONS==('git','file_read','file_patch','shell'),'preconditions_explicit')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));s=inspect_javascript_typescript_project(src);req(s['javascript_file_count']>=3 and s['typescript_file_count']>=1 and s['package_json_present'] and s['tsconfig_present'],'project_shape_detected');req(s['browser_api_marker_count']>=2 and s['async_marker_count']>=2 and s['state_management_marker_count']>=1,'browser_async_state_detected');req(s['inspection_only'] and not s['network_contacted'] and not s['dependency_installed'],'inspection_side_effect_free');bad=args(src,runtime,grant,{k:v for k,v in pres.items() if k!='shell'},git);r=run_javascript_typescript_implementation(**bad);req(not r['ok'] and r['status']=='complete_javascript_typescript_preconditions_required' and not r['action_executed'] and not r['release_authorized'],'missing_precondition_blocks')
 print({'ok':True,'suite':'v1342.0-2-javascript-typescript-foundations','passed':p[0],'total':5})
if __name__=='__main__':main()
