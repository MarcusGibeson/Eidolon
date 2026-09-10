from __future__ import annotations
import copy,hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from development_backlog_generation import generate_development_backlog
from priority_selection import generate_backlog_and_priority_selection,generate_priority_selection
from priority_selection_foundations import PRIORITY_DENIED_AUTHORITY,select_priority_from_backlog,validate_priority_selection
from priority_selection_reliability import build_priority_selection_operator_handoff,check_priority_selection_freshness,deterministic_concurrent_selection_digests,inspect_priority_selection_health,validate_priority_selection_reliability
CHECKS=[]
def req(v,l):
    if not v: raise AssertionError(l)
    CHECKS.append(l)
def reseal_backlog(row):
    row['backlog_digest']=hashlib.sha256(json.dumps({k:v for k,v in row.items() if k!='backlog_digest'},sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest();return row
def reseal_selection(row):
    row['selection_digest']=hashlib.sha256(json.dumps({k:v for k,v in row.items() if k!='selection_digest'},sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest();return row
def sig():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file():
            r=p.relative_to(ROOT).as_posix()
            if r.startswith('data/') or '__pycache__' in r or r.endswith(('.pyc','.pyo')): continue
            rows.append((r,hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
before=sig()
with tempfile.TemporaryDirectory(prefix='eidolon-v1263-reliability-') as td:
    p=Path(td)/('deep-'+'x'*45)/('nested-'+'y'*45)/('project-'+'z'*45);(p/'tests').mkdir(parents=True);(p/'docs').mkdir()
    (p/'pyproject.toml').write_text('[project]\nname="demo"\n',encoding='utf-8');(p/'app.py').write_text('def ok(): return True\n',encoding='utf-8');(p/'tests'/'test_app.py').write_text('def test_ok(): assert True\n',encoding='utf-8');(p/'docs'/'architecture.md').write_text('# A\nTODO investigate.\n',encoding='utf-8')
    backlog,selection=generate_backlog_and_priority_selection(p)
    rel=validate_priority_selection_reliability(selection,backlog);req(rel['ok'],'reliability_valid')
    fresh=check_priority_selection_freshness(selection,backlog,p);req(fresh['ok'] and not fresh['stale'],'fresh_selection_recognized')
    (p/'app.py').write_text('def ok(): return False\n',encoding='utf-8')
    stale=check_priority_selection_freshness(selection,backlog,p);req(not stale['ok'] and stale['stale'] and not stale['source_fresh'],'stale_source_detected')
    rebuilt_backlog,rebuilt_selection=generate_backlog_and_priority_selection(p)
    req(rebuilt_selection['selection_digest']==generate_priority_selection(p)['selection_digest'],'restart_duplicate_deterministic')
    req(not validate_priority_selection(selection,rebuilt_backlog)['ok'],'old_selection_rejected_against_changed_backlog')
    tampered=copy.deepcopy(rebuilt_selection);tampered['evaluations'][0]['net_score']+=999
    req(not validate_priority_selection(tampered,rebuilt_backlog)['ok'],'tampered_selection_rejected')
    resealed=copy.deepcopy(rebuilt_selection);resealed['evaluations'][0]['net_score']+=999;resealed['evaluations'][0]['evaluation_digest']=hashlib.sha256(json.dumps({k:v for k,v in resealed['evaluations'][0].items() if k!='evaluation_digest'},sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest();reseal_selection(resealed)
    req(not validate_priority_selection(resealed,rebuilt_backlog)['ok'],'resealed_score_tamper_rejected_semantically')
    concurrent=deterministic_concurrent_selection_digests(lambda: generate_priority_selection(p),workers=8)
    req(concurrent['ok'] and concurrent['attempt_count']==8 and concurrent['unique_selection_digest_count']==1,'concurrent_duplicates_converge')
    near=generate_priority_selection(p,priority_context=[{'objective_code':'triage_observed_maintenance_and_limitation_signals','user_value':'critical','urgency':'high','reversibility':'high','evidence_digest':'8'*64}])
    req(near['status']=='priority_selected' and near['near_tie'] and near['selection_margin']==1 and near['selection_confidence']=='low','near_tie_low_confidence_explicit')
    tie=generate_priority_selection(p,external_evidence=[
      {'kind':'tests','status':'failing','claim_code':'suite_a','polarity':'supports','confidence':'high','evidence_digest':'a'*64},
      {'kind':'tests','status':'failing','claim_code':'suite_b','polarity':'supports','confidence':'high','evidence_digest':'b'*64},
    ])
    req(tie['status']=='no_defensible_selection_tie' and tie['selected_work_item_id'] is None,'exact_tie_fails_closed')
    conflict_backlog,conflict_sel=generate_backlog_and_priority_selection(p,external_evidence=[
      {'kind':'tests','status':'failing','claim_code':'conflict','polarity':'supports','confidence':'high','evidence_digest':'c'*64},
      {'kind':'tests','status':'passing','claim_code':'conflict','polarity':'contradicts','confidence':'high','evidence_digest':'d'*64},
    ])
    blocked=[x for x in conflict_sel['evaluations'] if x['dependency_readiness']=='blocked'];req(blocked and all(x['work_item_id']!=conflict_sel['selected_work_item_id'] for x in blocked),'blocked_dependency_never_selected')
    cyclic=copy.deepcopy(conflict_backlog);a,b=cyclic['items'][0],cyclic['items'][1];a['dependency_item_ids']=[b['work_item_id']];b['dependency_item_ids']=[a['work_item_id']]
    for row in (a,b): row['work_item_digest']=hashlib.sha256(json.dumps({k:v for k,v in row.items() if k!='work_item_digest'},sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
    reseal_backlog(cyclic)
    try: select_priority_from_backlog(cyclic)
    except ValueError as exc: req(str(exc)=='invalid_development_backlog','dependency_cycle_backlog_rejected')
    else: req(False,'dependency_cycle_backlog_rejected')
    try: generate_priority_selection(p,priority_context=[{'objective_code':'triage_observed_maintenance_and_limitation_signals','urgency':'999'}])
    except ValueError as exc: req(str(exc)=='priority_context_value_invalid','extreme_factor_rejected')
    else: req(False,'extreme_factor_rejected')
    health=inspect_priority_selection_health(source_root=ROOT);req(health['ok'] and all(health['checks'].values()),'health_ready')
    handoff=build_priority_selection_operator_handoff(source_root=ROOT);req(handoff['ok'] and handoff['next_bounded_unit']=='v1264 Alternative Planning and Simulation','operator_handoff_ready')
    req(len(handoff['desktop_focus'])>=6,'desktop_focus_bounded_and_complete')
    for k,v in PRIORITY_DENIED_AUTHORITY.items(): req(rebuilt_selection[k] is v,f'{k}_denied')
req(sig()==before,'reliability_suite_preserves_source')
print(json.dumps({'ok':True,'suite':'v1263.6-v1263.8-priority-selection-reliability','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'commands_executed':False,'proposal_created':False,'schedule_created':False,'release_authorized':False},indent=2,sort_keys=True))
