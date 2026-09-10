from __future__ import annotations
import hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from evidence_based_project_inspection import build_evidence_based_project_assessment,public_project_assessment,validate_project_assessment
from evidence_based_project_inspection_foundations import DENIED_AUTHORITY
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
with tempfile.TemporaryDirectory(prefix='eidolon-v1261-integration-') as td:
    p=Path(td)/'web';(p/'tests').mkdir(parents=True);(p/'docs').mkdir();
    (p/'package.json').write_text('{"scripts":{"test":"node tests/app.test.js"}}',encoding='utf-8')
    (p/'index.html').write_text('<main><button>Go</button></main>',encoding='utf-8')
    (p/'app.js').write_text('export const add=(a,b)=>a+b;',encoding='utf-8')
    (p/'styles.css').write_text('main{max-width:40rem}',encoding='utf-8')
    (p/'tests'/'app.test.js').write_text('/* test fixture */',encoding='utf-8')
    (p/'docs'/'architecture.md').write_text('# Architecture',encoding='utf-8')
    assessment=build_evidence_based_project_assessment(p,external_evidence=[
        {'kind':'runtime_health','status':'healthy','claim_code':'runtime_startup','polarity':'supports','confidence':'high','evidence_digest':'1'*64},
        {'kind':'operator_feedback','status':'present','claim_code':'operator_usability','polarity':'supports','confidence':'medium','evidence_digest':'2'*64},
        {'kind':'tests','status':'passing','claim_code':'focused_tests','polarity':'supports','confidence':'high','evidence_digest':'3'*64},
        {'kind':'development_session','status':'completed','claim_code':'recent_campaign','polarity':'supports','confidence':'high','evidence_digest':'4'*64},
        {'kind':'known_limitation','status':'present','claim_code':'windows_native_review','polarity':'supports','confidence':'high','evidence_digest':'5'*64},
    ])
    req(assessment['ok'] and assessment['status']=='evidence_based_project_assessment_ready','assessment_ready')
    req(assessment['project_type'] in {'javascript_web_project','javascript_project'},'web_project_detected')
    req(validate_project_assessment(assessment)['ok'],'assessment_digest_valid')
    codes={c['claim_code']:c for c in assessment['claims']}
    req('runtime_health_unknown' not in codes and codes['runtime_health_observed']['claim_class']=='observed','runtime_health_explicitly_observed')
    req('operator_feedback_unknown' not in codes and codes['operator_feedback_observed']['claim_class']=='observed','operator_feedback_explicitly_observed')
    req('executed_test_outcome_unknown' not in codes and codes['executed_test_outcome_observed']['claim_class']=='observed','test_outcome_explicitly_observed')
    req('development_session_history_unknown' not in codes and codes['development_session_history_observed']['claim_class']=='observed','session_history_explicitly_observed')
    req(codes['known_limitations_observed']['claim_class']=='observed','known_limitation_explicitly_observed')
    req(not assessment['assessment_creates_development_proposal'] and not assessment['assessment_creates_backlog'],'assessment_does_not_autogenerate_work')
    req(not assessment['raw_external_content_stored'] and not assessment['raw_test_output_stored'] and not assessment['raw_operator_feedback_stored'],'external_payload_minimized')
    req(not assessment['private_runtime_discovery_performed'],'runtime_inputs_explicit_only')
    pub=public_project_assessment(assessment)
    req(pub['content_minimized'] and not pub['raw_content_exposed'] and not pub['private_runtime_content_exposed'],'public_assessment_minimized')
    req(pub['contradiction_count']==0,'clean_evidence_has_no_contradiction')
    conflict=build_evidence_based_project_assessment(p,external_evidence=[
        {'kind':'tests','status':'passing','claim_code':'full_suite','polarity':'supports','evidence_digest':'a'*64},
        {'kind':'tests','status':'failing','claim_code':'full_suite','polarity':'contradicts','evidence_digest':'b'*64},
    ])
    req(conflict['contradiction_count']==1 and conflict['contradiction_codes']==['full_suite'],'conflicting_evidence_retained')
    req(any(c['claim_class']=='unknown' and c['claim_code']=='conflicting_evidence:full_suite' for c in conflict['claims']),'contradiction_becomes_unknown_not_fake_resolution')
    minimal=build_evidence_based_project_assessment(p)
    req(minimal['evidence_gap_count']>=4,'missing_runtime_feedback_test_session_evidence_remains_unknown')
    req(any(c['claim_class']=='assumed' for c in minimal['claims']),'assumption_explicit')
    bad=dict(assessment);bad['project_type']='forged';req(not validate_project_assessment(bad)['ok'],'tampered_assessment_rejected')
    for k,v in DENIED_AUTHORITY.items(): req(assessment[k] is v,f'{k}_denied')
req(sig()==before,'integration_suite_preserves_source')
print(json.dumps({'ok':True,'suite':'v1261.3-v1261.5-evidence-based-project-inspection-integration','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'commands_executed':False,'project_modified':False,'proposal_created':False,'release_authorized':False},indent=2,sort_keys=True))
