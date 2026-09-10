from __future__ import annotations
import shutil,sys,tempfile,threading
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1337_browser_validation_test_support import *
from browser_validation import *
from ordinary_chat_development_campaign import _read_json,_atomic_json

def main():
 p=[0]
 def req(x,n): assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,candidate,pre=browser_candidate(Path(td));browser=shutil.which('chromium')
  external=validate_browser_candidate(wid,target={'kind':'loopback_url','url':'https://example.com/'},active_grant=grant,precondition_record_id=pre,browser_executable=browser,runtime_root=runtime,now_unix=101);req(not external['ok'] and external['status']=='external_browser_target_rejected' and external['action_executed'] is False,'external_network_rejected_prelaunch')
  bad=validate_browser_candidate(wid,target={'kind':'offline_document','html_relative_path':'ui.html'},active_grant=grant,precondition_record_id=pre,checks=[{'kind':'visible','selector':'#missing'}],browser_executable=browser,runtime_root=runtime,now_unix=102);req(not bad['ok'] and bad['browser_validation']['failure_domain']=='product_ui','product_failure_distinguished')
  missing=validate_browser_candidate(wid,target={'kind':'offline_document','html_relative_path':'ui.html'},active_grant=grant,precondition_record_id=pre,browser_executable='/definitely/missing/chromium',runtime_root=runtime,now_unix=103);req(not missing['ok'] and missing['browser_validation']['failure_domain']=='browser_tool','browser_tool_failure_distinguished')
  class H(BaseHTTPRequestHandler):
   def do_GET(self):
    body=b'<html><body><div id="ok">loopback</div></body></html>';self.send_response(200);self.send_header('content-type','text/html');self.send_header('content-length',str(len(body)));self.end_headers();self.wfile.write(body)
   def log_message(self,*a):pass
  server=ThreadingHTTPServer(('127.0.0.1',0),H);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   loop=validate_browser_candidate(wid,target={'kind':'loopback_url','url':f'http://127.0.0.1:{server.server_address[1]}/'},active_grant=grant,precondition_record_id=pre,checks=[{'kind':'visible','selector':'#ok'}],browser_executable=browser,fallback_html_relative_path='ui.html',runtime_root=runtime,now_unix=104);lr=loop['browser_validation'];req((loop['ok'] and lr['loopback_navigation_validated']) or (loop['status']=='browser_validation_policy_limited' and lr['failure_domain']=='browser_policy' and lr['offline_fallback_rendered'] and not lr['loopback_navigation_validated']),'managed_policy_or_real_loopback_distinguished')
  finally:server.shutdown();server.server_close()
  from browser_validation import _record_path
  good=validate_browser_candidate(wid,target={'kind':'offline_document','html_relative_path':'ui.html'},active_grant=grant,precondition_record_id=pre,checks=[{'kind':'attached','selector':'#go'}],browser_executable=browser,runtime_root=runtime,now_unix=105);gid=good['browser_validation']['browser_validation_id'];path=_record_path(gid,runtime);raw=_read_json(path);raw['checks_passed']=999;_atomic_json(path,raw);req(load_browser_validation(gid,runtime_root=runtime)=={},'tamper_rejected')
 print({'ok':True,'suite':'v1337.6-8-browser-validation-reliability','passed':p[0],'total':5})
if __name__=='__main__':main()
