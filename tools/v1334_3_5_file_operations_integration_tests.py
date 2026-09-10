from __future__ import annotations
import codecs,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1334_file_operations_test_support import *
from v1333_workspace_isolation_test_support import precondition
from structured_file_operations import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
passed=0
def req(x,n):
 global passed
 assert x,n;passed+=1
def cfg(src):
 (src/'crlf.txt').write_bytes(b'a\r\nb\r\n');(src/'bom.txt').write_bytes(codecs.BOM_UTF8+b'hello\n')
with tempfile.TemporaryDirectory() as td:
 src,runtime,grant,wid,root=candidate(Path(td),configure=cfg);wp=precondition(runtime,'file_patch')
 d=sha(root/'crlf.txt');r=patch_candidate_file(wid,'crlf.txt',expected_content_digest=d,patches=[{'type':'replace_text','old':'a\nb','new':'x\ny'}],active_grant=grant,precondition_record_id=wp,runtime_root=runtime,now_unix=101);req(r['ok'] and (root/'crlf.txt').read_bytes()==b'x\r\ny\r\n','crlf_preserved')
 d=sha(root/'bom.txt');r=patch_candidate_file(wid,'bom.txt',expected_content_digest=d,patches=[{'type':'replace_text','old':'hello','new':'hi'}],active_grant=grant,precondition_record_id=wp,runtime_root=runtime,now_unix=101);req(r['ok'] and (root/'bom.txt').read_bytes().startswith(codecs.BOM_UTF8),'utf8_bom_preserved')
 d=sha(root/'README.md');m=move_candidate_file(wid,'README.md','docs/README.md',expected_source_digest=d,active_grant=grant,precondition_record_id=wp,runtime_root=runtime,now_unix=101);req(m['ok'] and not (root/'README.md').exists() and (root/'docs/README.md').is_file(),'safe_move')
 g=update_generated_file(wid,'generated/report.json','{"ok": true}\n',expected_absent=True,active_grant=grant,precondition_record_id=wp,runtime_root=runtime,now_unix=101);req(g['ok'] and (root/'generated/report.json').is_file(),'generated_update')
 chat=process_ordinary_chat_development_turn('inspect file operation',project_state={'file_operation_id':g['file_operation']['operation_id']},runtime_root=runtime);req(chat.get('active') is True and chat['operation_executed_this_request'] is False and chat['file_operation']['raw_content_exposed'] is False,'ordinary_chat_inspection_only')
print({'ok':True,'suite':'v1334.3-5-file-operations-integration','passed':passed,'total':5})
