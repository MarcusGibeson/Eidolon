from __future__ import annotations
import copy,hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from development_backlog_generation import generate_development_backlog
from priority_selection_foundations import FACTOR_WEIGHTS,PRIORITY_DENIED_AUTHORITY,public_priority_selection,select_priority_from_backlog,validate_priority_selection
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
with tempfile.TemporaryDirectory(prefix='eidolon-v1263-foundations-') as td:
    p=Path(td)/'project';(p/'tests').mkdir(parents=True);(p/'docs').mkdir()
    (p/'pyproject.toml').write_text('[project]\nname="demo"\n',encoding='utf-8')
    (p/'app.py').write_text('def ok(): return True\n',encoding='utf-8')
    (p/'tests'/'test_app.py').write_text('def test_ok(): assert True\n',encoding='utf-8')
    (p/'docs'/'architecture.md').write_text('# Architecture\nTODO investigate maintenance signal.\n',encoding='utf-8')
    backlog=generate_development_backlog(p)
    req(backlog['item_count']==2,'two_candidate_fixture_ready')
    original=copy.deepcopy(backlog)
    selection=select_priority_from_backlog(backlog);valid=validate_priority_selection(selection,backlog);pub=public_priority_selection(selection)
    req(selection['status']=='priority_selected','priority_selected')
    req(valid['ok'] and valid['digest_valid'] and valid['lineage_valid'],'selection_valid')
    req(selection['selected_work_item_id'] is not None,'selected_item_present')
    chosen=next(x for x in selection['evaluations'] if x['work_item_id']==selection['selected_work_item_id'])
    req(chosen['objective_code']=='acquire_current_test_outcome_evidence','evidence_acquisition_outranks_maintenance_default')
    req(chosen['priority_rank']==1,'selected_rank_one')
    req(set(chosen['factors'])==set(FACTOR_WEIGHTS),'factor_contract_complete')
    req(chosen['benefit_score']>chosen['cost_score'],'benefit_and_cost_explicit')
    req(chosen['factors']['user_value']['epistemic_status']=='inferred','default_user_value_marked_inferred')
    req(all(x['dependency_readiness'] in {'ready','blocked'} for x in selection['evaluations']),'dependency_readiness_present')
    req(backlog==original,'backlog_not_mutated')
    req(all(x['priority'] is None and x['rank'] is None for x in backlog['items']),'v1262_backlog_remains_unranked')
    req(not selection['schedule_created'] and not selection['development_proposal_created'] and not selection['execution_started'] and not selection['project_modified'],'selection_creates_no_action')
    req(pub['content_minimized'] and not pub['raw_evidence_content_exposed'] and not pub['raw_paths_exposed'],'public_projection_minimized')
    req(pub['selected_work_item_id']==selection['selected_work_item_id'],'public_projection_selection_bound')
    maintenance=next(x for x in backlog['items'] if x['objective_code']=='triage_observed_maintenance_and_limitation_signals')
    context=[{'objective_code':maintenance['objective_code'],'user_value':'critical','urgency':'high','reversibility':'high','evidence_digest':'a'*64}]
    contextual=select_priority_from_backlog(backlog,priority_context=context)
    req(contextual['status']=='priority_selected','contextual_selection_ready')
    contextual_chosen=next(x for x in contextual['evaluations'] if x['work_item_id']==contextual['selected_work_item_id'])
    req(contextual_chosen['objective_code']==maintenance['objective_code'],'explicit_value_can_change_priority')
    req(contextual_chosen['factors']['user_value']['basis']=='explicit_bounded_context','explicit_context_basis_recorded')
    req(contextual_chosen['factors']['user_value']['epistemic_status']=='observed_input','explicit_context_epistemic_status')
    req(contextual_chosen['priority_context_evidence_digest']=='a'*64,'context_evidence_digest_bound')
    req(contextual['selection_digest']!=selection['selection_digest'],'context_change_changes_selection_digest')
    tie_backlog=generate_development_backlog(p,external_evidence=[
      {'kind':'tests','status':'failing','claim_code':'suite_a','polarity':'supports','confidence':'high','evidence_digest':'1'*64},
      {'kind':'tests','status':'failing','claim_code':'suite_b','polarity':'supports','confidence':'high','evidence_digest':'2'*64},
    ])
    tie=select_priority_from_backlog(tie_backlog)
    req(tie['status']=='no_defensible_selection_tie','exact_tie_explicit')
    req(tie['selected_work_item_id'] is None and len(tie['tied_work_item_ids'])==2,'tie_selects_nothing')
    req(all(next(x for x in tie['evaluations'] if x['work_item_id']==wid)['priority_rank']==1 for wid in tie['tied_work_item_ids']),'tie_rank_shared')
    empty=generate_development_backlog(p,external_evidence=[{'kind':'tests','status':'passing','claim_code':'suite','polarity':'supports','confidence':'high','evidence_digest':'3'*64}])
    # remove the maintenance marker for a genuinely empty backlog
    (p/'docs'/'architecture.md').write_text('# Architecture\n',encoding='utf-8')
    empty=generate_development_backlog(p,external_evidence=[{'kind':'tests','status':'passing','claim_code':'suite','polarity':'supports','confidence':'high','evidence_digest':'3'*64}])
    empty_sel=select_priority_from_backlog(empty)
    req(empty['item_count']==0 and empty_sel['status']=='no_defensible_selection_empty_backlog','empty_backlog_no_selection')
    req(empty_sel['selected_work_item_id'] is None,'empty_selection_none')
    try: select_priority_from_backlog(backlog,priority_context=[{'objective_code':'not_a_real_item','user_value':'high'}])
    except ValueError as exc: req(str(exc)=='priority_context_objective_invalid_or_duplicate','unknown_context_rejected')
    else: req(False,'unknown_context_rejected')
    try: select_priority_from_backlog(backlog,priority_context=[{'objective_code':maintenance['objective_code'],'user_value':'infinite'}])
    except ValueError as exc: req(str(exc)=='priority_context_value_invalid','invalid_factor_band_rejected')
    else: req(False,'invalid_factor_band_rejected')
    tampered=copy.deepcopy(selection);tampered['selection_confidence']='omniscient'
    req(not validate_priority_selection(tampered,backlog)['ok'],'tampered_selection_rejected')
    second=select_priority_from_backlog(backlog)
    req(second['selection_digest']==selection['selection_digest'],'duplicate_selection_idempotent')
    for k,v in PRIORITY_DENIED_AUTHORITY.items(): req(selection[k] is v,f'{k}_denied')
req(sig()==before,'foundation_suite_preserves_source')
print(json.dumps({'ok':True,'suite':'v1263.0-v1263.2-priority-selection-foundations','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'commands_executed':False,'proposal_created':False,'schedule_created':False,'release_authorized':False},indent=2,sort_keys=True))
