from __future__ import annotations
import shutil,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1337_browser_validation_test_support import *
from browser_validation import *

def main():
 p=[0]
 def req(x,n): assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,candidate,pre=browser_candidate(Path(td));before=sorted((x.relative_to(src).as_posix(),x.read_bytes()) for x in src.rglob('*') if x.is_file())
  r=validate_browser_candidate(wid,target={'kind':'offline_document','html_relative_path':'ui.html'},active_grant=grant,precondition_record_id=pre,interactions=[{'op':'fill','selector':'#name','value':'checkpoint'},{'op':'click','selector':'#go'}],checks=[{'kind':'text_equals','selector':'#out','expected':'Hello checkpoint'},{'kind':'visible','selector':'#go'}],browser_executable=shutil.which('chromium'),runtime_root=runtime,now_unix=101);row=r['browser_validation'];req(r['ok'] and row['checks_passed']==2,'integrated_browser_checkpoint')
  req(row['screenshot_captured'] and row['screenshot_digest'] and row['screenshot_bytes']>0,'reproducible_visual_evidence')
  req(row['external_requests_blocked']>=0 and row['external_network_authorized'] is False,'network_boundary_preserved')
  after=sorted((x.relative_to(src).as_posix(),x.read_bytes()) for x in src.rglob('*') if x.is_file());req(before==after,'selected_source_immutable')
  req(row['approval_granted'] is False and row['release_authorized'] is False and row['independent_authority_granted'] is False,'authority_not_derived')
 print({'ok':True,'suite':'v1337.9-browser-validation-checkpoint','passed':p[0],'total':5})
if __name__=='__main__':main()
