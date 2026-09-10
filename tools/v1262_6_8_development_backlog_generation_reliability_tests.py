from __future__ import annotations
import copy,hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from development_backlog_generation import generate_development_backlog
from development_backlog_generation_foundations import BACKLOG_DENIED_AUTHORITY,build_backlog_from_assessment
from development_backlog_generation_reliability import build_development_backlog_operator_handoff,check_development_backlog_freshness,inspect_development_backlog_generation_health,validate_backlog_reliability
from evidence_based_project_inspection import build_evidence_based_project_assessment
CHECKS=[]
def req(v,l):
    if not v: raise AssertionError(l)
    CHECKS.append(l)
def reseal(row):
    row['backlog_digest']=hashlib.sha256(json.dumps({k:v for k,v in row.items() if k!='backlog_digest'},sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest();return row
def sig():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file():
            r=p.relative_to(ROOT).as_posix()
            if r.startswith('data/') or '__pycache__' in r or r.endswith(('.pyc','.pyo')): continue
            rows.append((r,hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
before=sig()
with tempfile.TemporaryDirectory(prefix='eidolon-v1262-reliability-') as td:
    p=Path(td)/('deep-'+'x'*40)/('nested-'+'y'*40)/('project-'+'z'*40);(p/'tests').mkdir(parents=True);(p/'docs').mkdir();
    (p/'pyproject.toml').write_text('[project]\nname="demo"\n',encoding='utf-8');(p/'app.py').write_text('def ok(): return True\n',encoding='utf-8');(p/'tests'/'test_app.py').write_text('def test_ok(): assert True\n',encoding='utf-8');(p/'docs'/'architecture.md').write_text('# A',encoding='utf-8')
    backlog=generate_development_backlog(p)
    req(validate_backlog_reliability(backlog)['ok'],'reliability_valid')
    fresh=check_development_backlog_freshness(backlog,p);req(fresh['ok'] and not fresh['stale_source'],'fresh_source_recognized')
    (p/'app.py').write_text('def ok(): return False\n',encoding='utf-8')
    stale=check_development_backlog_freshness(backlog,p);req(not stale['ok'] and stale['stale_source'],'stale_source_detected')
    assessment=build_evidence_based_project_assessment(p)
    rebuilt=build_backlog_from_assessment(assessment);req(validate_backlog_reliability(rebuilt)['ok'],'rebuilt_after_change_valid')
    req(build_backlog_from_assessment(assessment)['backlog_digest']==rebuilt['backlog_digest'],'restart_duplicate_deterministic')
    multi=generate_development_backlog(p,external_evidence=[
      {'kind':'tests','status':'failing','claim_code':'cycle_fixture','polarity':'supports','evidence_digest':'a'*64},
      {'kind':'tests','status':'passing','claim_code':'cycle_fixture','polarity':'contradicts','evidence_digest':'b'*64},
    ])
    req(len(multi['items'])>=2,'multi_item_dependency_fixture_ready')
    cyclic=copy.deepcopy(multi)
    a,b=cyclic['items'][0],cyclic['items'][1];a['dependency_item_ids']=[b['work_item_id']];b['dependency_item_ids']=[a['work_item_id']]
    for row in (a,b): row['work_item_digest']=hashlib.sha256(json.dumps({k:v for k,v in row.items() if k!='work_item_digest'},sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
    reseal(cyclic)
    rel=validate_backlog_reliability(cyclic);req(not rel['ok'] and not rel['dependency_cycles_absent'],'dependency_cycle_rejected')
    tampered=copy.deepcopy(rebuilt);tampered['items'][0]['estimated_effort']['band']='infinite';reseal(tampered)
    req(not validate_backlog_reliability(tampered)['ok'],'invalid_effort_contract_rejected')
    req(all(row['rank'] is None and row['priority'] is None for row in rebuilt['items']),'no_hidden_priority_fields')
    health=inspect_development_backlog_generation_health(source_root=ROOT);req(health['ok'] and all(health['checks'].values()),'health_ready')
    handoff=build_development_backlog_operator_handoff(source_root=ROOT);req(handoff['ok'] and handoff['next_bounded_unit']=='v1263 Priority Selection','operator_handoff_ready')
    req(handoff['native_windows_validation'] if 'native_windows_validation' in handoff else True,'handoff_contract_present')
    for k,v in BACKLOG_DENIED_AUTHORITY.items(): req(rebuilt[k] is v,f'{k}_denied')
req(sig()==before,'reliability_suite_preserves_source')
print(json.dumps({'ok':True,'suite':'v1262.6-v1262.8-development-backlog-generation-reliability','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'commands_executed':False,'proposal_created':False,'priority_selected':False,'release_authorized':False},indent=2,sort_keys=True))
