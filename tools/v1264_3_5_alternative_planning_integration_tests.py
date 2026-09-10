from __future__ import annotations
import hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from alternative_planning import generate_alternative_plan,generate_priority_and_alternative_plan,inspect_alternative_planning
from alternative_planning_foundations import PLAN_DENIED_AUTHORITY,validate_alternative_plan
CHECKS=[]
def req(v,l):
    if not v: raise AssertionError(l)
    CHECKS.append(l)
def sig():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file():
            r=p.relative_to(ROOT).as_posix()
            if r.startswith('data/') or '__pycache__' in r or r.endswith(('.pyc','.pyo')): continue
            rows.append((r,hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
before=sig()
with tempfile.TemporaryDirectory(prefix='eidolon-v1264-integration-') as td:
    p=Path(td)/'project';(p/'tests').mkdir(parents=True);(p/'docs').mkdir();(p/'pyproject.toml').write_text('[project]\nname="demo"\n',encoding='utf-8');(p/'app.py').write_text('def ok(): return True\n',encoding='utf-8');(p/'tests'/'test_app.py').write_text('def test_ok(): assert True\n',encoding='utf-8');(p/'docs'/'architecture.md').write_text('# A\nTODO inspect.\n',encoding='utf-8')
    backlog,selection,plan=generate_priority_and_alternative_plan(p)
    req(validate_alternative_plan(plan,selection,backlog)['ok'],'full_v1261_v1262_v1263_v1264_lineage_valid')
    req(selection['selected_work_item_id']==plan['selected_work_item_id'],'selected_priority_drives_plan')
    req(plan['category']=='evidence_acquisition','baseline_selected_category_expected')
    req({x['strategy_code'] for x in plan['approaches']}=={'focused_existing_verification','layered_focused_then_regression','fresh_extract_validation_campaign'},'evidence_acquisition_has_three_competing_approaches')
    selected=next(x for x in plan['approaches'] if x['approach_id']==plan['selected_approach_id'])
    req(selected['strategy_code']=='focused_existing_verification','minimal_evidence_plan_selected')
    req(plan['selection_margin']==2 and plan['selection_confidence']=='low','near_plan_tradeoff_exposed')
    req(all(x['factor_basis']=='deterministic_strategy_simulation' for x in plan['approaches']),'default_simulation_basis_explicit')
    contextual=generate_alternative_plan(p,plan_context=[{'strategy_code':'layered_focused_then_regression','success_confidence':'critical','effort':'small','risk':'low','uncertainty':'low','reversibility':'high','evidence_digest':'d'*64}])
    chosen=next(x for x in contextual['approaches'] if x['approach_id']==contextual['selected_approach_id'])
    req(chosen['strategy_code']=='layered_focused_then_regression','bounded_plan_context_can_change_choice')
    req(chosen['factor_basis']=='explicit_bounded_context' and chosen['plan_context_evidence_digest']=='d'*64,'plan_context_provenance_recorded')
    inspected=inspect_alternative_planning(p)
    req(inspected['ok'] and inspected['status']=='alternative_planning_inspection_ready','read_only_planning_inspection_ready')
    req(inspected['public_plan']['content_minimized'],'inspection_projection_content_minimized')
    # Contradictory evidence must make evidence-resolution the priority and yield resolution-specific alternatives.
    cb,cs,cp=generate_priority_and_alternative_plan(p,external_evidence=[
      {'kind':'tests','status':'failing','claim_code':'suite','polarity':'supports','confidence':'high','evidence_digest':'e'*64},
      {'kind':'tests','status':'passing','claim_code':'suite','polarity':'contradicts','confidence':'high','evidence_digest':'f'*64},
    ])
    req(cp['category']=='evidence_resolution','conflict_priority_becomes_resolution_plan')
    req('reproduce_conflicting_signal_under_same_conditions' in {x['strategy_code'] for x in cp['approaches']},'conflict_plan_has_reproduction_strategy')
    req(all(x['work_item_id']==cs['selected_work_item_id'] for x in cp['approaches']),'all_approaches_bound_to_selected_work')
    # Failing runtime evidence creates reliability planning when operator priority context makes it the selected item.
    rb,rs,rp=generate_priority_and_alternative_plan(p,external_evidence=[{'kind':'runtime_health','status':'failed','claim_code':'startup','polarity':'supports','confidence':'high','evidence_digest':'1'*64}],priority_context=[{'objective_code':'investigate_runtime_health_signal:startup','user_value':'critical','urgency':'critical','reversibility':'medium','evidence_digest':'2'*64}])
    req(rp['category']=='reliability_candidate','reliability_priority_gets_repair_strategies')
    req('diagnose_then_minimal_repair' in {x['strategy_code'] for x in rp['approaches']},'diagnostic_minimal_repair_strategy_present')
    req(any(fm['failure_code']=='symptom_repaired_not_cause' for x in rp['approaches'] for fm in x['predicted_failure_modes']),'repair_failure_mode_predicted')
    # Changed evidence must revise all lineage rather than reusing stale plan.
    changed=generate_alternative_plan(p,external_evidence=[{'kind':'tests','status':'passing','claim_code':'suite','polarity':'supports','confidence':'high','evidence_digest':'3'*64}])
    req(changed['plan_digest']!=plan['plan_digest'],'changed_evidence_revises_plan')
    second=generate_alternative_plan(p)
    req(second['plan_digest']==plan['plan_digest'],'restart_regeneration_deterministic')
    req(not plan['development_proposal_created'] and not plan['schedule_created'] and not plan['execution_started'],'planning_creates_no_action')
    for k,v in PLAN_DENIED_AUTHORITY.items(): req(plan[k] is v,f'{k}_denied')
req(sig()==before,'integration_suite_preserves_source')
print(json.dumps({'ok':True,'suite':'v1264.3-v1264.5-alternative-planning-integration','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'commands_executed':False,'proposal_created':False,'schedule_created':False,'release_authorized':False},indent=2,sort_keys=True))
