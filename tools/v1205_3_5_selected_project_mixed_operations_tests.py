from __future__ import annotations
import hashlib,json,shutil,sys,tempfile,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from grounded_development_planning import create_or_resume_grounded_plan
from javascript_tool_implementation_checkpoint import run_or_resume_javascript_tool_implementation_checkpoint
from selected_project_apply import create_or_resume_apply_request,authorize_and_apply_selected_project,create_or_resume_rollback_request,authorize_and_rollback_selected_project
from small_project_capability_registry import capability_for_project_kind
from selected_project_change_planning import parse_change_directives,safe_relative_path
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
def tree_sig(root):
 h=hashlib.sha256()
 for p in sorted(root.rglob('*')):
  if p.is_file(): h.update(p.relative_to(root).as_posix().encode()); h.update(hashlib.sha256(p.read_bytes()).digest())
 return h.hexdigest()
def approve(rt,project,request):
 turn=process_ordinary_chat_development_turn(request,action_projection={'intent':{'category':'action_request'}},session_id='mixed',project_state={'id':'selected-js','path':str(project)},runtime_root=rt)
 p=turn['proposal']; a=process_ordinary_chat_development_turn(f"Approve development proposal {p['proposal_id']} revision 1.",runtime_root=rt); require(a['event']=='approval_consumed',a); return p
def provider(calls):
 def gen(prompt):
  calls.append(1); payload=json.loads(prompt); content={'cli.js':"if (process.argv.includes('--help')) console.log('usage'); else console.log('updated');\n",'lib/new.js':"exports.value = 2;\n",'legacy.js':''}; ops={'cli.js':'modify','lib/new.js':'create','legacy.js':'delete'}
  require(set(payload['planned_paths'])==set(content),payload['planned_paths'])
  return json.dumps({'authority':payload['authority'],'files':[{'path':p,'operation':ops[p],'content':content[p]} for p in payload['planned_paths']]})
 return gen
existing=[{'relative_path':'cli.js'},{'relative_path':'legacy.js'}]
require([r['operation'] for r in parse_change_directives('Modify `cli.js`, create `lib/new.js`, delete `legacy.js`',existing)]==['modify','create','delete'])
require(safe_relative_path('lib/new.js')=='lib/new.js')
for bad in ('../x.js','C:/x.js','/tmp/x.js','notes.exe'):
 try: safe_relative_path(bad); require(False,bad)
 except ValueError: require(True)
for request,reason in [('create `cli.js`','create_target_exists'),('modify `missing.js`','modify_target_missing'),('delete `missing.js`','delete_target_missing'),('modify `cli.js`, delete `CLI.js`','duplicate_change_path')]:
 try: parse_change_directives(request,existing); require(False,request)
 except ValueError as exc: require(str(exc)==reason,(request,str(exc)))
rt=Path(tempfile.mkdtemp(prefix='eid-v1205-mixed-'))
try:
 project=rt/'project'; (project/'tests').mkdir(parents=True); (project/'lib').mkdir(); (project/'package.json').write_text(json.dumps({'name':'selected-tool','version':'1.0.0','bin':{'selected-tool':'cli.js'}})); (project/'cli.js').write_text("if (process.argv.includes('--help')) console.log('old usage');\n"); (project/'legacy.js').write_text("module.exports = 'legacy';\n"); (project/'tests/tool.test.js').write_text("const assert=require('assert'); assert.equal(1,1);\n")
 before=tree_sig(project); p=approve(rt,project,'Build this Node CLI: modify `cli.js`, create `lib/new.js`, delete `legacy.js`')
 plan=create_or_resume_grounded_plan(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt); require(plan['project_kind']=='javascript_tool_project',plan); require(capability_for_project_kind(plan['project_kind']).capability_id=='javascript_tool'); require([x['operation'] for x in plan['file_plan']]==['modify','create','delete']); require(tree_sig(project)==before)
 calls=[]; final=run_or_resume_javascript_tool_implementation_checkpoint(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],action='retain',runtime_root=rt,provider_generate=provider(calls),node_executable=shutil.which('node') or 'node'); require(final['ok'] is True,final); require(final['disposition_action']=='retain'); require(len(calls)==1); require(tree_sig(project)==before)
 ar=create_or_resume_apply_request(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_implementation_checkpoint_digest=final['implementation_checkpoint_digest'],runtime_root=rt); require(ar['ok'] is True,ar); require(ar['operation_count']==3)
 applied=authorize_and_apply_selected_project(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_apply_request_digest=ar['apply_request_digest'],authorization_phrase=f"APPLY {p['proposal_id']} REVISION 1 REQUEST {ar['apply_request_digest']}",runtime_root=rt); require(applied['ok'] is True,applied); require((project/'lib/new.js').is_file()); require(not (project/'legacy.js').exists()); require('updated' in (project/'cli.js').read_text())
 rr=create_or_resume_rollback_request(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_apply_result_digest=applied['apply_result_digest'],runtime_root=rt); require(rr['ok'] is True,rr)
 rolled=authorize_and_rollback_selected_project(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],expected_rollback_request_digest=rr['rollback_request_digest'],authorization_phrase=f"ROLLBACK {p['proposal_id']} REVISION 1 REQUEST {rr['rollback_request_digest']}",runtime_root=rt); require(rolled['ok'] is True,rolled); require(tree_sig(project)==before); require((project/'legacy.js').is_file()); require(not (project/'lib/new.js').exists())
finally: shutil.rmtree(rt,ignore_errors=True)
rt=Path(tempfile.mkdtemp(prefix='eid-v1205-invalid-'))
try:
 project=rt/'project'; project.mkdir(); (project/'cli.js').write_text("console.log('x')\n"); before=tree_sig(project); p=approve(rt,project,'Build me a Node tool: delete `missing.js`'); rejected=create_or_resume_grounded_plan(p['proposal_id'],expected_revision=1,expected_revision_digest=p['revision_digest'],runtime_root=rt); require(rejected['status']=='change_plan_rejected',rejected); require(rejected['reason']=='delete_target_missing'); require(tree_sig(project)==before)
finally: shutil.rmtree(rt,ignore_errors=True)
registry=(ROOT/'conscious_agent/small_project_capability_registry.py').read_text(); require('"javascript_tool_project"' in registry); require('selected_project_supported=True' in registry)
verifier=(ROOT/'tools/post_review_development_verify.py').read_text(); require('v1205.3-v1205.5' in verifier); require('v1205_3_5_selected_project_mixed_operations_tests.py' in verifier)
release=(ROOT/'tools/release_verify.py').read_text(); require(release.count('v1205.5-selected-project-mixed-operations')==2)
metadata=(ROOT/'conscious_agent/release_metadata.py').read_text(); require('WORKING_SOURCE_VERSION = "1205.5"' in metadata)
print(json.dumps({'ok':True,'version':'1205.5','checks':len(CHECKS),'passed':sum(CHECKS),'elapsed_seconds':round(time.monotonic()-START,4),'selected_javascript_supported':True,'mixed_operations':['create','modify','delete'],'release_authorized':False,'authority_granted':False},sort_keys=True))
