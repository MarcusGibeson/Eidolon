from __future__ import annotations
import hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from priority_selection import generate_backlog_and_priority_selection,generate_priority_selection,inspect_priority_selection
from priority_selection_foundations import PRIORITY_DENIED_AUTHORITY,validate_priority_selection
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
with tempfile.TemporaryDirectory(prefix='eidolon-v1263-integration-') as td:
    p=Path(td)/'project';(p/'tests').mkdir(parents=True);(p/'docs').mkdir()
    (p/'pyproject.toml').write_text('[project]\nname="demo"\n',encoding='utf-8')
    (p/'app.py').write_text('def ok(): return True\n',encoding='utf-8')
    (p/'tests'/'test_app.py').write_text('def test_ok(): assert True\n',encoding='utf-8')
    (p/'docs'/'architecture.md').write_text('# Architecture\nTODO operator-visible maintenance signal.\n',encoding='utf-8')
    backlog,selection=generate_backlog_and_priority_selection(p)
    req(validate_priority_selection(selection,backlog)['ok'],'integrated_selection_valid')
    req(selection['backlog_generated_in_same_read_only_pass'],'backlog_same_read_only_pass')
    req(selection['priority_is_judgment_not_authority'],'priority_judgment_boundary_explicit')
    req(selection['alternative_planning_deferred_to_v1264'],'v1264_planning_deferred')
    req(selection['selected_work_item_id']==next(x['work_item_id'] for x in backlog['items'] if x['objective_code']=='acquire_current_test_outcome_evidence'),'default_real_backlog_selection')
    req(selection['selection_reason_codes']==['unique_highest_eligible_net_score'],'selection_reason_explicit')
    req(selection['comparative_rationale'] and selection['comparative_rationale'][0]['selected_net_score_advantage']>0,'comparative_rationale_present')
    req(all(x['priority'] is None and x['rank'] is None for x in backlog['items']),'integration_does_not_mutate_backlog_ranks')
    maintenance=next(x for x in backlog['items'] if x['objective_code']=='triage_observed_maintenance_and_limitation_signals')
    contextual=generate_priority_selection(p,priority_context=[{'objective_code':maintenance['objective_code'],'user_value':'critical','urgency':'high','reversibility':'high','evidence_digest':'4'*64}])
    chosen=next(x for x in contextual['evaluations'] if x['work_item_id']==contextual['selected_work_item_id'])
    req(chosen['objective_code']==maintenance['objective_code'],'explicit_operator_value_changes_selection')
    req(contextual['near_tie'] and contextual['selection_confidence']=='low' and contextual['selection_margin']==1,'near_tie_exposed')
    inspected=inspect_priority_selection(p)
    req(inspected['ok'] and inspected['status']=='priority_selection_inspection_ready','read_only_inspection_ready')
    req(inspected['public_selection']['content_minimized'],'inspection_projection_minimized')
    conflict_backlog,conflict_selection=generate_backlog_and_priority_selection(p,external_evidence=[
      {'kind':'tests','status':'failing','claim_code':'full_suite','polarity':'supports','confidence':'high','evidence_digest':'5'*64},
      {'kind':'tests','status':'passing','claim_code':'full_suite','polarity':'contradicts','confidence':'high','evidence_digest':'6'*64},
    ])
    resolution=next(x for x in conflict_backlog['items'] if x['category']=='evidence_resolution')
    repair=next(x for x in conflict_backlog['items'] if x['objective_code']=='investigate_test_signal:full_suite')
    repair_eval=next(x for x in conflict_selection['evaluations'] if x['work_item_id']==repair['work_item_id'])
    req(resolution['work_item_id'] in repair['dependency_item_ids'],'conflict_dependency_preserved')
    req(repair_eval['dependency_readiness']=='blocked' and not repair_eval['eligible'],'dependent_repair_blocked')
    req(conflict_selection['selected_work_item_id']==resolution['work_item_id'],'evidence_resolution_selected_before_dependent_repair')
    req(not conflict_selection['development_proposal_created'] and not conflict_selection['schedule_created'],'selection_creates_no_proposal_or_schedule')
    with_passing=generate_priority_selection(p,external_evidence=[{'kind':'tests','status':'passing','claim_code':'suite','polarity':'supports','confidence':'high','evidence_digest':'7'*64}])
    req(with_passing['backlog_digest']!=selection['backlog_digest'],'changed_evidence_changes_backlog_lineage')
    req(with_passing['selection_digest']!=selection['selection_digest'],'changed_evidence_revises_selection')
    second=generate_priority_selection(p)
    req(second['selection_digest']==selection['selection_digest'],'restart_regeneration_deterministic')
    for k,v in PRIORITY_DENIED_AUTHORITY.items(): req(selection[k] is v,f'{k}_denied')
req(sig()==before,'integration_suite_preserves_source')
print(json.dumps({'ok':True,'suite':'v1263.3-v1263.5-priority-selection-integration','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'commands_executed':False,'proposal_created':False,'schedule_created':False,'release_authorized':False},indent=2,sort_keys=True))
