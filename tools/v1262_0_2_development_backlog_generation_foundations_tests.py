from __future__ import annotations
import hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from evidence_based_project_inspection import build_evidence_based_project_assessment
from development_backlog_generation_foundations import BACKLOG_DENIED_AUTHORITY,BACKLOG_CATEGORIES,MAX_BACKLOG_ITEMS,build_backlog_from_assessment,public_development_backlog,validate_development_backlog
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
with tempfile.TemporaryDirectory(prefix='eidolon-v1262-foundation-') as td:
    p=Path(td)/'project';(p/'src').mkdir(parents=True);(p/'docs').mkdir();
    (p/'pyproject.toml').write_text('[project]\nname="demo"\n',encoding='utf-8')
    (p/'README.md').write_text('# Demo\nKnown limitation: fixture.\n',encoding='utf-8')
    (p/'src'/'broken.py').write_text('def broken(:\n# TODO repair\n',encoding='utf-8')
    assessment=build_evidence_based_project_assessment(p)
    backlog=build_backlog_from_assessment(assessment); valid=validate_development_backlog(backlog); pub=public_development_backlog(backlog)
    req(backlog['ok'] and backlog['status']=='development_backlog_ready','backlog_ready')
    req(valid['ok'] and valid['digest_valid'],'backlog_digest_valid')
    req(0 < backlog['item_count'] <= MAX_BACKLOG_ITEMS,'backlog_bounded')
    req(all(row['category'] in BACKLOG_CATEGORIES for row in backlog['items']),'categories_bounded')
    req(any(row['objective_code']=='repair_observed_python_parse_failures' for row in backlog['items']),'parse_failure_becomes_candidate')
    req(any(row['objective_code']=='review_absent_test_surface' for row in backlog['items']),'missing_test_surface_becomes_review_candidate')
    req(any(row['objective_code']=='triage_observed_maintenance_and_limitation_signals' for row in backlog['items']),'maintenance_signal_becomes_investigation')
    req(all(row['acceptance_criteria'] for row in backlog['items']),'acceptance_criteria_present')
    req(all('dependency_item_ids' in row for row in backlog['items']),'dependencies_present')
    req(all('risk_codes' in row and row['risk_band'] in {'low','medium','high','unknown'} for row in backlog['items']),'risk_contract_present')
    req(all((row['uncertainty'] or {}).get('level') in {'low','medium','high'} for row in backlog['items']),'uncertainty_present')
    req(all((row['estimated_effort'] or {}).get('band') in {'small','medium','large','unknown'} for row in backlog['items']),'effort_present')
    req(all(row['priority'] is None and row['rank'] is None for row in backlog['items']),'priority_not_selected')
    req(not backlog['development_proposal_created'] and not backlog['execution_started'] and not backlog['project_modified'],'no_action_created')
    req(backlog['ordering_semantics']=='deterministic_non_priority','deterministic_not_priority')
    req(not backlog['raw_source_content_stored'] and not backlog['raw_evidence_content_stored'],'content_minimized')
    req(pub['content_minimized'] and not pub['raw_evidence_content_exposed'] and not pub['raw_paths_exposed'],'public_projection_minimized')
    for k,v in BACKLOG_DENIED_AUTHORITY.items(): req(backlog[k] is v,f'{k}_denied')
    second=build_backlog_from_assessment(assessment)
    req(second['backlog_digest']==backlog['backlog_digest'],'duplicate_generation_idempotent')
    req([x['work_item_id'] for x in second['items']]==[x['work_item_id'] for x in backlog['items']],'work_item_ids_deterministic')
    tampered=dict(backlog);tampered['item_count']=999
    req(not validate_development_backlog(tampered)['ok'],'tamper_rejected')
req(sig()==before,'foundation_suite_preserves_source')
print(json.dumps({'ok':True,'suite':'v1262.0-v1262.2-development-backlog-generation-foundations','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'commands_executed':False,'proposal_created':False,'priority_selected':False,'release_authorized':False},indent=2,sort_keys=True))
