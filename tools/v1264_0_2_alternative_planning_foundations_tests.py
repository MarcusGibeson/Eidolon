from __future__ import annotations
import copy,hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from priority_selection import generate_backlog_and_priority_selection
from alternative_planning_foundations import PLAN_DENIED_AUTHORITY,build_alternative_plan,public_alternative_plan,validate_alternative_plan
CHECKS=[]
def req(v,l):
    if not v: raise AssertionError(l)
    CHECKS.append(l)
def reseal_approach(row):
    row['approach_digest']=hashlib.sha256(json.dumps({k:v for k,v in row.items() if k!='approach_digest'},sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def reseal_plan(row):
    row['plan_digest']=hashlib.sha256(json.dumps({k:v for k,v in row.items() if k!='plan_digest'},sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
with tempfile.TemporaryDirectory(prefix='eidolon-v1264-foundations-') as td:
    p=Path(td)/'project';(p/'tests').mkdir(parents=True);(p/'docs').mkdir();(p/'pyproject.toml').write_text('[project]\nname="demo"\n',encoding='utf-8');(p/'app.py').write_text('def ok(): return True\n',encoding='utf-8');(p/'tests'/'test_app.py').write_text('def test_ok(): assert True\n',encoding='utf-8');(p/'docs'/'architecture.md').write_text('# Architecture\nTODO bounded followup.\n',encoding='utf-8')
    backlog,selection=generate_backlog_and_priority_selection(p)
    req(selection['status']=='priority_selected','priority_precondition_selected')
    plan=build_alternative_plan(selection,backlog);valid=validate_alternative_plan(plan,selection,backlog);pub=public_alternative_plan(plan)
    req(valid['ok'] and valid['semantic_valid'],'alternative_plan_valid')
    req(plan['status']=='alternative_plan_selected' and plan['selected_approach_id'],'unique_approach_selected')
    req(2 <= plan['approach_count'] <= 4,'multiple_bounded_approaches')
    req(len({x['strategy_code'] for x in plan['approaches']})==plan['approach_count'],'approaches_distinct')
    req(all(x['implementation_steps'] and x['verification_steps'] for x in plan['approaches']),'requirements_connected_to_steps_and_verification')
    req(all(x['predicted_failure_modes'] for x in plan['approaches']),'failure_modes_predicted')
    req(all(fm['epistemic_status']=='predicted' for x in plan['approaches'] for fm in x['predicted_failure_modes']),'predictions_not_observations')
    req(plan['assumptions'] and plan['completion_conditions'] and plan['blocker_conditions'],'assumptions_completion_blockers_present')
    req(pub['content_minimized'] and not pub['raw_paths_exposed'] and not pub['raw_source_content_exposed'],'public_projection_minimized')
    req(pub['predicted_failure_mode_count']>=plan['approach_count'],'public_failure_count_bounded')
    req(plan['selection_digest']==selection['selection_digest'] and plan['backlog_digest']==backlog['backlog_digest'],'exact_lineage_bound')
    req(plan['selected_work_item_id']==selection['selected_work_item_id'],'exact_work_item_bound')
    req(plan['selection_confidence'] in {'low','medium','high'},'selection_confidence_explicit')
    req(plan['comparative_rationale'],'comparative_rationale_present')
    # Exact plan tie from explicit bounded planning context must fail closed.
    codes=[x['strategy_code'] for x in plan['approaches']]
    tie_context=[]
    for code in codes:
        tie_context.append({'strategy_code':code,'success_confidence':'medium','effort':'medium','risk':'medium','uncertainty':'medium','reversibility':'medium','evidence_digest':'a'*64})
    tied=build_alternative_plan(selection,backlog,plan_context=tie_context)
    req(tied['status']=='no_defensible_plan_approach_tie' and tied['selected_approach_id'] is None,'exact_approach_tie_fails_closed')
    req(validate_alternative_plan(tied,selection,backlog)['ok'],'tie_plan_still_valid')
    # A priority tie yields no plan rather than inventing a winner.
    tb,ts=generate_backlog_and_priority_selection(p,external_evidence=[
      {'kind':'tests','status':'failing','claim_code':'suite_a','polarity':'supports','confidence':'high','evidence_digest':'b'*64},
      {'kind':'tests','status':'failing','claim_code':'suite_b','polarity':'supports','confidence':'high','evidence_digest':'c'*64},
    ])
    req(ts['status']=='no_defensible_selection_tie','priority_tie_fixture_ready')
    no_plan=build_alternative_plan(ts,tb)
    req(no_plan['status']=='no_defensible_plan_no_priority_selection' and no_plan['approaches']==[],'no_priority_means_no_plan')
    req(validate_alternative_plan(no_plan,ts,tb)['ok'],'no_plan_contract_valid')
    tampered=copy.deepcopy(plan);tampered['approaches'][0]['simulation_score']+=100
    req(not validate_alternative_plan(tampered,selection,backlog)['ok'],'unsealed_score_tamper_rejected')
    resealed=copy.deepcopy(plan);resealed['approaches'][0]['simulation_score']+=100;reseal_approach(resealed['approaches'][0]);reseal_plan(resealed)
    req(not validate_alternative_plan(resealed,selection,backlog)['ok'],'resealed_score_tamper_rejected_semantically')
    badfm=copy.deepcopy(plan);fm=badfm['approaches'][0]['predicted_failure_modes'][0];fm['likelihood']='impossible_magic';fm['failure_mode_digest']=hashlib.sha256(json.dumps({k:v for k,v in fm.items() if k!='failure_mode_digest'},sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest();reseal_approach(badfm['approaches'][0]);reseal_plan(badfm)
    req(not validate_alternative_plan(badfm,selection,backlog)['ok'],'resealed_failure_semantics_tamper_rejected')
    for k,v in PLAN_DENIED_AUTHORITY.items(): req(plan[k] is v,f'{k}_denied')
print(json.dumps({'ok':True,'suite':'v1264.0-v1264.2-alternative-planning-foundations','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'commands_executed':False,'proposal_created':False,'plan_execution_authorized':False,'release_authorized':False},indent=2,sort_keys=True))
