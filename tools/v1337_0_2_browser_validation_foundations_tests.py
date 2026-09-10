from __future__ import annotations
import shutil,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1337_browser_validation_test_support import *
from browser_validation import *

def main():
 p=[0]
 def req(x,n): assert x,n;p[0]+=1
 req(TARGET_KINDS==('offline_document','loopback_url') and INTERACTION_KINDS==('click','fill','press'),'typed_surface')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,candidate,pre=browser_candidate(Path(td));before=(src/'ui.html').read_bytes();browser=shutil.which('chromium')
  result=validate_browser_candidate(wid,target={'kind':'offline_document','html_relative_path':'ui.html'},active_grant=grant,precondition_record_id=pre,interactions=[{'op':'fill','selector':'#name','value':'Eidolon'},{'op':'click','selector':'#go'}],checks=[{'kind':'text_equals','selector':'#out','expected':'Hello Eidolon'}],browser_executable=browser,runtime_root=runtime,now_unix=101)
  row=result['browser_validation'];req(result['ok'] and row['browser_launched'] and row['page_rendered'],'real_chromium_rendered')
  req(row['checks_passed']==1 and row['checks_failed']==0 and row['screenshot_captured'],'typed_interaction_and_screenshot')
  req(row['raw_url_exposed'] is False and row['raw_selector_exposed'] is False and row['interaction_values_exposed'] is False and row['network_authorized'] is False,'content_minimized_no_external_network')
  req((src/'ui.html').read_bytes()==before and row['selected_source_modified'] is False,'selected_source_unchanged')
 print({'ok':True,'suite':'v1337.0-2-browser-validation-foundations','passed':p[0],'total':5})
if __name__=='__main__':main()
