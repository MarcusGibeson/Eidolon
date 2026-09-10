from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1333_workspace_isolation_test_support import WS,make_source,active_grant,precondition
from workspace_isolation import create_disposable_workspace,_record_path
from ordinary_chat_development_campaign import _read_json

SERVER='''from __future__ import annotations\nimport os,sys,time\nfrom http.server import ThreadingHTTPServer,BaseHTTPRequestHandler\nmode=sys.argv[1] if len(sys.argv)>1 else "ok"\nif mode=="exit": raise SystemExit(3)\ndelay=float(sys.argv[2]) if len(sys.argv)>2 else 0.0\nif delay: time.sleep(delay)\nhost=os.environ.get("EIDOLON_SERVICE_HOST","127.0.0.1");port=int(os.environ["EIDOLON_SERVICE_PORT"])\nclass H(BaseHTTPRequestHandler):\n def do_GET(self):\n  if self.path=="/health":\n   body=b"ok";self.send_response(200);self.send_header("content-length",str(len(body)));self.end_headers();self.wfile.write(body)\n  else:self.send_response(404);self.end_headers()\n def log_message(self,*a):pass\nThreadingHTTPServer((host,port),H).serve_forever()\n'''

def service_candidate(base:Path):
 src=make_source(base);(src/'service_fixture.py').write_text(SERVER,encoding='utf-8');runtime=base/'runtime';grant=active_grant(commands=('service','shell'));isopre=precondition(runtime,'file_patch')
 made=create_disposable_workspace(source_root=src,source_workspace_digest=WS,active_grant=grant,precondition_record_id=isopre,mode='filesystem_copy',runtime_root=runtime,now_unix=101);assert made['ok'],made
 rec=_read_json(_record_path(made['workspace_id'],runtime));candidate=Path(rec['candidate_private_path']);servicepre=precondition(runtime,'service');shellpre=precondition(runtime,'shell')
 return src,runtime,grant,made['workspace_id'],candidate,servicepre,shellpre

def definition(code='api',deps=(),mode='ok',port=0,readiness=2.5):
 return {'service_code':code,'argv':[sys.executable,'-u','service_fixture.py',mode],'dependencies':list(deps),'requested_port':port,'readiness':{'kind':'http','path':'/health','expected_status':200},'readiness_timeout_seconds':readiness,'process_timeout_seconds':30}
