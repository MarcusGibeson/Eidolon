from __future__ import annotations
import copy,hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from alternative_planning import generate_alternative_plan,generate_priority_and_alternative_plan
from alternative_planning_foundations import PLAN_DENIED_AUTHORITY,validate_alternative_plan
from alternative_planning_reliability import build_alternative_planning_operator_handoff,check_alternative_plan_freshness,deterministic_concurrent_plan_digests,inspect_alternative_planning_health,validate_alternative_plan_reliability
CHECKS=[]
def req(v,l):
    if not v: raise AssertionError(l)
    CHECKS.append(l)
def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def reseal_plan(row): row['plan_digest']=digest({k:v for k,v in row.items() if k!='plan_digest'});return row
with tempfile.TemporaryDirectory(prefix='eidolon-v1264-reliability-') as td:
    p=Path(td)/('deep-'+'x'*45)/('nested-'+'y'*45)/('project-'+'z'*45);(p/'tests').mkdir(parents=True);(p/'docs').mkdir();(p/'pyproject.toml').write_text('[project]\nname="demo"\n',encoding='utf-8');(p/'app.py').write_text('def ok(): return True\n',encoding='utf-8');(p/'tests'/'test_app.py').write_text('def test_ok(): assert True\n',encoding='utf-8');(p/'docs'/'architecture.md').write_text('# A\nTODO inspect.\n',encoding='utf-8')
    backlog,selection,plan=generate_priority_and_alternative_plan(p)
    rel=validate_alternative_plan_reliability(plan,selection,backlog);req(rel['ok'],'reliability_valid')
    fresh=check_alternative_plan_freshness(plan,selection,backlog,p);req(fresh['ok'] and not fresh['stale'],'fresh_plan_recognized')
    (p/'app.py').write_text('def ok(): return False\n',encoding='utf-8')
    stale=check_alternative_plan_freshness(plan,selection,backlog,p);req(not stale['ok'] and stale['stale'] and not stale['source_fresh'],'stale_source_invalidates_plan')
    nb,ns,np=generate_priority_and_alternative_plan(p)
    req(np['plan_digest']==generate_alternative_plan(p)['plan_digest'],'restart_duplicate_deterministic')
    req(not validate_alternative_plan(plan,ns,nb)['ok'],'old_plan_rejected_against_changed_priority_lineage')
    concurrent=deterministic_concurrent_plan_digests(lambda: generate_alternative_plan(p),workers=8)
    req(concurrent['ok'] and concurrent['attempt_count']==8 and concurrent['unique_plan_digest_count']==1,'concurrent_duplicates_converge')
    # Rescored/resealed tamper is still rejected semantically.
    tampered=copy.deepcopy(np);tampered['approaches'][0]['simulation_score']+=999;tampered['approaches'][0]['approach_digest']=digest({k:v for k,v in tampered['approaches'][0].items() if k!='approach_digest'});reseal_plan(tampered)
    req(not validate_alternative_plan(tampered,ns,nb)['ok'],'resealed_score_tamper_rejected')
    # Failure prediction cannot be converted into an observed fact even if all digests are recomputed.
    semantic=copy.deepcopy(np);fm=semantic['approaches'][0]['predicted_failure_modes'][0];fm['epistemic_status']='observed';fm['failure_mode_digest']=digest({k:v for k,v in fm.items() if k!='failure_mode_digest'});semantic['approaches'][0]['approach_digest']=digest({k:v for k,v in semantic['approaches'][0].items() if k!='approach_digest'});reseal_plan(semantic)
    req(not validate_alternative_plan(semantic,ns,nb)['ok'],'predicted_failure_cannot_be_resealed_as_observed')
    # Explicit exact tie remains no-plan.
    base=generate_alternative_plan(p);ctx=[]
    for row in base['approaches']: ctx.append({'strategy_code':row['strategy_code'],'success_confidence':'medium','effort':'medium','risk':'medium','uncertainty':'medium','reversibility':'medium','evidence_digest':'4'*64})
    tied=generate_alternative_plan(p,plan_context=ctx)
    req(tied['status']=='no_defensible_plan_approach_tie' and tied['selected_approach_id'] is None,'strategy_tie_fails_closed')
    try: generate_alternative_plan(p,plan_context=[{'strategy_code':'not_a_real_strategy','risk':'low'}])
    except ValueError as exc: req(str(exc)=='plan_context_strategy_invalid_or_duplicate','unknown_strategy_context_rejected')
    else: req(False,'unknown_strategy_context_rejected')
    try: generate_alternative_plan(p,plan_context=[{'strategy_code':base['approaches'][0]['strategy_code'],'risk':'galactic'}])
    except ValueError as exc: req(str(exc)=='plan_context_band_invalid','extreme_plan_factor_rejected')
    else: req(False,'extreme_plan_factor_rejected')
    req(len(str(p))>180,'long_path_fixture_exercised')
    health=inspect_alternative_planning_health(source_root=ROOT);req(health['ok'] and all(health['checks'].values()),'health_ready')
    handoff=build_alternative_planning_operator_handoff(source_root=ROOT);req(handoff['ok'] and handoff['next_bounded_unit']=='v1265 Isolated Self-Modification','operator_handoff_ready')
    req(len(handoff['desktop_focus'])>=8,'desktop_focus_complete')
    for k,v in PLAN_DENIED_AUTHORITY.items(): req(np[k] is v,f'{k}_denied')
print(json.dumps({'ok':True,'suite':'v1264.6-v1264.8-alternative-planning-reliability','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'commands_executed':False,'proposal_created':False,'execution_authorized':False,'release_authorized':False},indent=2,sort_keys=True))
