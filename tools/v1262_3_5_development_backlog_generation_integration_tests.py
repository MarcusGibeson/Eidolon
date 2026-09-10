from __future__ import annotations
import hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from development_backlog_generation import generate_development_backlog,inspect_development_backlog
from development_backlog_generation_foundations import BACKLOG_DENIED_AUTHORITY,validate_development_backlog
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
with tempfile.TemporaryDirectory(prefix='eidolon-v1262-integration-') as td:
    p=Path(td)/'web';(p/'tests').mkdir(parents=True);(p/'docs').mkdir();
    (p/'package.json').write_text('{"scripts":{"test":"node tests/app.test.js"}}',encoding='utf-8')
    (p/'index.html').write_text('<main><button>Go</button></main>',encoding='utf-8')
    (p/'app.js').write_text('export const add=(a,b)=>a+b;',encoding='utf-8')
    (p/'tests'/'app.test.js').write_text('/* fixture */',encoding='utf-8')
    (p/'docs'/'architecture.md').write_text('# Architecture',encoding='utf-8')
    ext=[
      {'kind':'tests','status':'failing','claim_code':'focused_suite','polarity':'supports','confidence':'high','evidence_digest':'1'*64},
      {'kind':'runtime_health','status':'degraded','claim_code':'startup_health','polarity':'supports','confidence':'high','evidence_digest':'2'*64},
      {'kind':'known_limitation','status':'present','claim_code':'windows_native_review','polarity':'supports','confidence':'high','evidence_digest':'3'*64},
    ]
    backlog=generate_development_backlog(p,external_evidence=ext)
    req(validate_development_backlog(backlog)['ok'],'integrated_backlog_valid')
    req(backlog['assessment_generated_in_same_read_only_pass'],'assessment_same_pass')
    req(backlog['backlog_is_candidate_work_only'] and backlog['priority_selection_deferred_to_v1263'],'candidate_only_priority_deferred')
    codes={row['objective_code'] for row in backlog['items']}
    req('investigate_test_signal:focused_suite' in codes,'failing_test_candidate_generated')
    req('investigate_runtime_health_signal:startup_health' in codes,'runtime_health_candidate_generated')
    req('review_known_limitation:windows_native_review' in codes,'known_limitation_candidate_generated')
    req(all(row['source_evidence_ids'] or row['objective_code'].startswith('review_absent_') for row in backlog['items']),'evidence_lineage_retained')
    req(all(not row['development_proposal_created'] and not row['execution_authorized'] and not row['application_authorized'] for row in backlog['items']),'items_grant_no_authority')
    req(not backlog['priority_selected'] and not backlog['schedule_created'],'no_priority_or_schedule')
    inspection=inspect_development_backlog(p,external_evidence=ext)
    req(inspection['ok'] and inspection['status']=='development_backlog_inspection_ready','public_inspection_ready')
    req(inspection['public_backlog']['content_minimized'],'public_backlog_minimized')
    conflict=generate_development_backlog(p,external_evidence=[
      {'kind':'tests','status':'failing','claim_code':'full_suite','polarity':'supports','evidence_digest':'a'*64},
      {'kind':'tests','status':'passing','claim_code':'full_suite','polarity':'contradicts','evidence_digest':'b'*64},
    ])
    resolution=next(row for row in conflict['items'] if row['objective_code']=='resolve_conflicting_evidence:full_suite')
    repair=next(row for row in conflict['items'] if row['objective_code']=='investigate_test_signal:full_suite')
    req(resolution['work_item_id'] in repair['dependency_item_ids'],'conflicting_test_candidate_depends_on_resolution')
    req(resolution['uncertainty']['level']=='high','conflict_uncertainty_high')
    req(not conflict['priority_selected'],'conflict_not_prioritized')
    second=generate_development_backlog(p,external_evidence=ext)
    req(second['backlog_digest']==backlog['backlog_digest'],'integrated_duplicate_idempotent')
    for k,v in BACKLOG_DENIED_AUTHORITY.items(): req(backlog[k] is v,f'{k}_denied')
req(sig()==before,'integration_suite_preserves_source')
print(json.dumps({'ok':True,'suite':'v1262.3-v1262.5-development-backlog-generation-integration','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'commands_executed':False,'proposal_created':False,'priority_selected':False,'release_authorized':False},indent=2,sort_keys=True))
