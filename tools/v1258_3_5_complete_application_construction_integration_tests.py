from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
os.environ['PYTHONDONTWRITEBYTECODE']='1'
for path in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(path) not in sys.path: sys.path.insert(0,str(path))

from complete_application_construction import load_complete_application_quality, public_complete_application_quality
from complete_application_construction_foundations import load_complete_application_construction
from complete_application_construction_reliability import build_complete_application_operator_handoff
from diagnostic_repair_reasoning_foundations import load_diagnostic_result
from isolated_coding_execution import authorize_and_run_isolated_coding_execution, load_isolated_coding_review
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1258_test_support import make_web_project, prepare_complete_web_request, tree_signature

CHECKS=[]
def require(v,label):
    if not v: raise AssertionError(label)
    CHECKS.append(label)

def source_signature():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(ROOT).as_posix()
        if '__pycache__' in rel or rel.endswith(('.pyc','.pyo')) or rel.startswith('data/'): continue
        rows.append((rel,hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()

GOOD_HTML="""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calculator</title><link rel="stylesheet" href="styles.css"></head>
<body><main class="app"><h1>Calculator</h1><label for="a">First number</label><input id="a" inputmode="decimal"><label for="b">Second number</label><input id="b" inputmode="decimal"><label for="op">Operation</label><select id="op"><option value="add">Add</option><option value="subtract">Subtract</option><option value="multiply">Multiply</option><option value="divide">Divide</option></select><button id="calculate" type="button">Calculate</button><button id="clear" type="button">Clear</button><output id="result" aria-live="polite"></output></main><script src="app.js"></script></body></html>
"""
APP_JS="""function calculate(a,b,operation){
  const x=Number(a), y=Number(b);
  if(!Number.isFinite(x)||!Number.isFinite(y)) throw new Error('invalid-number');
  if(operation==='add') return x+y;
  if(operation==='subtract') return x-y;
  if(operation==='multiply') return x*y;
  if(operation==='divide'){ if(y===0) throw new Error('divide-by-zero'); return x/y; }
  throw new Error('unknown-operation');
}
function clearCalculator(){ return {a:'',b:'',result:''}; }
if(typeof document!=='undefined'){
  const byId=(id)=>document.getElementById(id);
  byId('calculate').addEventListener('click',()=>{ try{ byId('result').textContent=String(calculate(byId('a').value,byId('b').value,byId('op').value)); }catch(error){ byId('result').textContent=error.message; }});
  byId('clear').addEventListener('click',()=>{ byId('a').value=''; byId('b').value=''; byId('result').textContent=''; byId('a').focus(); });
}
if(typeof module!=='undefined') module.exports={calculate,clearCalculator};
"""
BAD_CSS="""*{box-sizing:border-box}body{font-family:system-ui,sans-serif;margin:0;padding:1rem}.app{width:90%;max-width:32rem;margin:auto;display:grid;gap:.75rem}input,select,button{font:inherit;padding:.65rem}output{min-height:2rem}\n"""
GOOD_CSS=BAD_CSS+"""button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid currentColor;outline-offset:2px}@media (max-width:36rem){.app{width:100%;margin:0}button{width:100%}}\n"""
PACKAGE=json.dumps({"name":"bounded-calculator","private":True,"scripts":{"test":"node --test"},"dependencies":{},"devDependencies":{}},sort_keys=True,indent=2)+"\n"
TEST_JS="""const test=require('node:test');const assert=require('node:assert/strict');const {calculate,clearCalculator}=require('../app.js');
test('calculator operations',()=>{assert.equal(calculate(2,3,'add'),5);assert.equal(calculate(7,2,'subtract'),5);assert.equal(calculate(4,3,'multiply'),12);assert.equal(calculate(8,2,'divide'),4)});
test('clear state',()=>assert.deepEqual(clearCalculator(),{a:'',b:'',result:''}));
"""
README="""# Calculator Web Application

A dependency-free calculator using plain HTML, CSS, and JavaScript.

## Run
Open `index.html` in a browser.

## Test
Run `node --test` from the project directory. The test suite covers arithmetic and clear-state behavior.
"""

class QualityRepairingProvider:
    def __init__(self): self.calls=0; self.prompts=[]
    def __call__(self,prompt:str)->str:
        payload=json.loads(prompt); self.calls+=1; self.prompts.append(payload); auth=payload['authority']
        construction=payload.get('application_construction') or {}
        if construction.get('construction_profile')!='web_application': raise AssertionError('construction contract missing from provider prompt')
        if self.calls==1:
            files=[
                {'path':'index.html','operation':'modify','content':GOOD_HTML},
                {'path':'app.js','operation':'create','content':APP_JS},
                {'path':'styles.css','operation':'create','content':BAD_CSS},
                {'path':'package.json','operation':'create','content':PACKAGE},
                {'path':'tests/app.test.js','operation':'create','content':TEST_JS},
                {'path':'README.md','operation':'create','content':README},
            ]
        else:
            diag=(payload.get('previous_outcome') or {}).get('diagnostic_context') or {}
            codes=set(diag.get('quality_failure_codes') or [])
            if not {'keyboard_focus_visible','responsive_breakpoint_present'} <= codes:
                raise AssertionError(f'quality repair context missing: {codes}')
            if diag.get('preferred_hypothesis_code') not in {'application_coherence_defect','incomplete_cross_file_artifact_set'}:
                raise AssertionError('construction diagnosis not preferred')
            files=[{'path':'styles.css','operation':'modify','content':GOOD_CSS}]
        return json.dumps({'authority':{'request_id':auth['request_id'],'execution_digest':auth['execution_digest'],'attempt':auth['attempt']},'files':files})

SOURCE_BEFORE=source_signature()
with tempfile.TemporaryDirectory(prefix='eid-v1258-3-5-') as d:
    base=Path(d); runtime=base/'runtime'; project=make_web_project(base); project_before=tree_signature(project)
    request,contract,prepared=prepare_complete_web_request(project,runtime)
    provider=QualityRepairingProvider()
    result=authorize_and_run_isolated_coding_execution(request['request_id'],expected_execution_digest=prepared['execution_digest'],authorization_phrase=prepared['authorization_phrase'],runtime_root=runtime,provider_generate=provider,node_executable='node')
    require(result['ok'] and result['status']=='isolated_coding_execution_completed','complete_application_execution_succeeds_after_quality_repair')
    require(provider.calls==2 and result['attempt_count']==2 and result['repair_attempt_count']==1,'one_initial_and_one_quality_repair_attempt')
    require(result['diagnostic_cycle_count']==1 and result['diagnostic_reasoning_used'],'construction_quality_failure_uses_v1257_diagnostic_loop')
    require(provider.prompts[0]['application_construction']['construction_contract_digest']==contract['construction_contract_digest'],'provider_prompt_bound_to_exact_construction_contract')
    require(provider.prompts[0]['limits']['no_dependency_installation'] and provider.prompts[0]['limits']['no_selected_project_application'],'provider_prompt_preserves_execution_boundaries')
    q1=load_complete_application_quality(request['request_id'],1,runtime_root=runtime); q2=load_complete_application_quality(request['request_id'],2,runtime_root=runtime)
    require(q1['passed'] is False and q2['passed'] is True,'quality_evidence_preserves_failed_then_passing_attempts')
    require({'keyboard_focus_visible','responsive_breakpoint_present'} <= set(q1['failed_finding_codes']),'first_attempt_identifies_accessibility_and_responsive_gaps')
    require(all(q2['dimension_results'].values()),'final_application_passes_all_required_quality_dimensions')
    require(q2['workspace_summary']['test_file_count']>=1 and q2['workspace_summary']['documentation_present'],'final_application_has_tests_and_documentation')
    require(q2['workspace_summary']['undeclared_external_dependency_count']==0,'final_application_has_no_undeclared_external_dependencies')
    public=public_complete_application_quality(q2)
    require(public['raw_file_contents_exposed'] is False and str(project) not in json.dumps(public),'public_quality_evidence_content_minimized')
    diagnosis=load_diagnostic_result(request['request_id'],1,runtime_root=runtime)
    require(diagnosis['repair_supported'] and diagnosis['preferred_hypothesis_code'] in {'application_coherence_defect','incomplete_cross_file_artifact_set'},'diagnosis_ranks_application_coherence_cause')
    quality_probe=next(row for row in diagnosis['probe_results'] if row['probe_code']=='construction_quality_recheck')
    require(quality_probe['passed'] is False and 'keyboard_focus_visible' in quality_probe['quality_failure_codes'],'diagnostic_recheck_reproduces_quality_gap')
    review=load_isolated_coding_review(request['request_id'],runtime_root=runtime)
    require(review['reviewable_diff_available'] and review['added_file_count']>=5,'multi_file_application_produces_reviewable_diff')
    require({'index.html','app.js','styles.css','package.json','tests/app.test.js','README.md'} <= set(review['changed_paths']),'review_contains_coherent_multi_file_artifact_set')
    require(tree_signature(project)==project_before,'complete_application_construction_keeps_selected_project_immutable')
    handoff=build_complete_application_operator_handoff(request['request_id'],runtime_root=runtime)
    require(handoff['ok'] and handoff['status']=='complete_application_operator_handoff_ready','operator_handoff_ready_after_complete_quality_pass')
    require(handoff['application_authorized'] is False and handoff['release_authorized'] is False,'complete_application_handoff_grants_no_apply_or_release_authority')

# Ordinary conversation automatically prepares the complete-app contract only
# when the request itself clearly asks for that broader outcome.
with tempfile.TemporaryDirectory(prefix='eid-v1258-3-5-chat-') as d:
    base=Path(d); runtime=base/'runtime'; project=make_web_project(base)
    projection={'grounding':{'grounding_status':'matched','capability_id':'software_development'},'intent':{'category':'action_request'}}
    created=process_ordinary_chat_development_turn('Build a complete responsive accessible web application for this calculator.',action_projection=projection,session_id='v1258-chat',project_state={'id':'webcalc','name':'Web Calculator','path':str(project)},runtime_root=runtime)
    require(created['active'] and created['event']=='proposal_created','ordinary_chat_complete_application_request_creates_proposal')
    proposal=created['proposal']
    approved=process_ordinary_chat_development_turn(f"Approve development proposal {proposal['proposal_id']} revision {proposal['revision']}.",runtime_root=runtime)
    require(approved['event']=='approval_consumed','ordinary_chat_proposal_approval_consumed')
    request_id=str(approved.get('isolated_coding_request_id') or '')
    chat_contract=load_complete_application_construction(request_id,runtime_root=runtime)
    require(bool(chat_contract) and chat_contract['construction_profile']=='web_application','ordinary_chat_bridge_prepares_complete_application_contract')
    require(chat_contract['provider_contact_authorized'] is False and chat_contract['application_authorized'] is False,'proposal_approval_does_not_grant_construction_execution_or_application')

require(source_signature()==SOURCE_BEFORE,'integration_suite_preserves_eidolon_source')
print(json.dumps({'ok':True,'suite':'v1258.3-v1258.5-complete-application-construction-integration','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_calls':2,'quality_repair_attempts':1,'selected_project_modified':False,'application_authorized':False,'release_authorized':False},indent=2,sort_keys=True))
