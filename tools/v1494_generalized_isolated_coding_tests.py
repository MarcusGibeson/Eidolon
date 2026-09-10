from __future__ import annotations
import os,sys,tempfile,shutil,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=Path(tempfile.mkdtemp(prefix='eidolon-v1494-'));os.environ['EIDOLON_DATA_DIR']=str(R/'runtime');os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True;sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.generalized_isolated_coding import validate_edit_contract,apply_structured_edits
from conscious_agent.development_authority import issue_operator_authorization,private_scope_digest
p=f=0
def ck(n,c,d=''):
 global p,f
 if c:p+=1;print('PASS',n)
 else:f+=1;print('FAIL',n,d)
try:
 w=R/'workspace';(w/'conscious_agent').mkdir(parents=True);src=w/'conscious_agent'/'sample.py';src.write_text('def alpha():\n    return 1\n',encoding='utf-8');unrelated=w/'KEEP.txt';unrelated.write_text('keep',encoding='utf-8');uh=hashlib.sha256(unrelated.read_bytes()).hexdigest()
 plan={'operator_selected':True,'candidate_id':'a','plan_digest':'a'*64,'source_module':'conscious_agent/sample.py','destination_module':'conscious_agent/sample_helpers.py'}
 edits=[{'path':'conscious_agent/sample.py','action':'modify','replacements':[{'find':'return 1','replace':'return helper()'}]},{'path':'conscious_agent/sample_helpers.py','action':'create','content':'def helper():\n    return 1\n'}]
 v=validate_edit_contract(plan,edits);ck('generalized edit contract accepts bounded source plus destination',v['ok'],v)
 phrase='Implement candidate a in this workspace.'
 receipt=issue_operator_authorization(stage='workspace_implementation',subject_id='a',subject_digest='a'*64,scope_digest=private_scope_digest(str(w.resolve())),explicit_operator_text=phrase,expected_operator_text=phrase)
 blocked=apply_structured_edits(w,plan,edits,workspace_authorization_receipt=None);ck('workspace edits require explicit authorization',blocked['status']=='blocked',blocked)
 r=apply_structured_edits(w,plan,edits,workspace_authorization_receipt=receipt);ck('authorized isolated coding modifies only workspace',r['status']=='workspace_changed' and r['workspace_only'] and not r['active_source_modified'],r)
 ck('structured coding supports modification and creation',src.read_text().find('helper()')>=0 and (w/'conscious_agent'/'sample_helpers.py').is_file(),r)
 ck('unrelated workspace file is preserved',hashlib.sha256(unrelated.read_bytes()).hexdigest()==uh,unrelated.read_text())
 bad=validate_edit_contract(plan,[{'path':'../data/private.py','action':'create','content':'x=1'}]);ck('private traversal path is rejected',not bad['ok'] and 'path_rejected' in bad['errors'],bad)
 out=validate_edit_contract(plan,[{'path':'conscious_agent/other.py','action':'create','content':'x=1'}]);ck('edits outside exact plan scope are rejected',not out['ok'] and 'path_outside_plan' in out['errors'],out)
 dupw=R/'dup';(dupw/'conscious_agent').mkdir(parents=True);(dupw/'conscious_agent'/'sample.py').write_text('x=1\nx=1\n',encoding='utf-8')
 dup_receipt=issue_operator_authorization(stage='workspace_implementation',subject_id='a',subject_digest='a'*64,scope_digest=private_scope_digest(str(dupw.resolve())),explicit_operator_text=phrase,expected_operator_text=phrase)
 dup=apply_structured_edits(dupw,plan,[{'path':'conscious_agent/sample.py','action':'modify','replacements':[{'find':'x=1','replace':'x=2'}]}],workspace_authorization_receipt=dup_receipt);ck('non-unique replacements fail before mutation',dup['status']=='blocked' and (dupw/'conscious_agent'/'sample.py').read_text()=='x=1\nx=1\n',dup)
 ck('coding receipt grants no install or promotion authority',not r['installation_authorized'] and not r['promotion_authorized'] and not r['provider_contacted'],r)
 print({'ok':f==0,'passed':p,'failed':f,'suite':'v1494-generalized-isolated-coding','content_free':True})
finally:shutil.rmtree(R,ignore_errors=True)
if f:raise SystemExit(1)
