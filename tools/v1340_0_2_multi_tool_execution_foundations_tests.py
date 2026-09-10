from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1340_multi_tool_execution_test_support import *
from multi_tool_execution import *

def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 req(REQUIRED_PRECONDITIONS==('git','file_patch','shell','browser','service'),'phase4_preconditions_explicit')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));args=campaign_args(src,runtime,grant,pres,git);bad=dict(args);bad['precondition_record_ids']={k:v for k,v in pres.items() if k!='browser'};r=run_multi_tool_execution(**bad);req(not r['ok'] and r['status']=='complete_phase4_preconditions_required' and r['action_executed'] is False,'missing_precondition_blocks_prelaunch')
  req(r['release_authorized'] is False and r['source_application_authorized'] is False,'prelaunch_no_authority')
  req(content_manifest(src)==content_manifest(src),'foundation_source_stable')
  req(MULTI_TOOL_DENIED_AUTHORITY['independent_authority_granted'] is False,'checkpoint_contract_not_autonomy_grant')
 print({'ok':True,'suite':'v1340.0-2-multi-tool-execution-foundations','passed':p[0],'total':5})
if __name__=='__main__':main()
