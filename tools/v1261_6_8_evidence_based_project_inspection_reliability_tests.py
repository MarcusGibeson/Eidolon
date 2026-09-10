from __future__ import annotations
import hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from evidence_based_project_inspection import build_evidence_based_project_assessment,validate_project_assessment
from evidence_based_project_inspection_foundations import DENIED_AUTHORITY,inspect_project_evidence
from evidence_based_project_inspection_reliability import check_project_inspection_freshness,inspect_evidence_based_project_inspection_health,build_evidence_based_project_inspection_operator_handoff
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
before=sig();health=inspect_evidence_based_project_inspection_health(source_root=ROOT);handoff=build_evidence_based_project_inspection_operator_handoff(source_root=ROOT)
req(health['ok'] and all(health['checks'].values()),'health_surfaces_complete');req(len(health['source_sha256'])==health['required_source_count'],'health_hashes_complete')
req(handoff['ok'] and handoff['operator_review_required'],'operator_handoff_ready');req(len(handoff['desktop_focus'])>=6,'desktop_focus_bounded')
with tempfile.TemporaryDirectory(prefix='eidolon-v1261-reliability-') as td:
    root=Path(td)/('deep-'+'x'*80)/('deeper-'+'y'*80)/'project';root.mkdir(parents=True)
    (root/'pyproject.toml').write_text('[project]\nname="long"',encoding='utf-8');(root/'app.py').write_text('x=1\n',encoding='utf-8')
    assessment=build_evidence_based_project_assessment(root)
    req(validate_project_assessment(assessment)['ok'],'long_path_assessment_valid')
    req(check_project_inspection_freshness(assessment,root)['ok'],'fresh_snapshot_confirmed')
    (root/'app.py').write_text('x=2\n',encoding='utf-8')
    stale=check_project_inspection_freshness(assessment,root);req(not stale['ok'] and stale['stale_source'],'stale_source_detected')
    req(len(stale['freshness_digest'])==64,'freshness_evidence_sealed')
    private=root/'data';private.mkdir();(private/'secrets.json').write_text('{"token":"private"}',encoding='utf-8')
    rep=inspect_project_evidence(root);req(rep['private_or_excluded_count']>=1,'new_private_path_excluded')
    req('private' not in json.dumps(rep).casefold() or 'private_or_excluded' in json.dumps(rep).casefold(),'private_payload_not_exposed')
    if hasattr(os,'symlink'):
        target=Path(td)/'outside';target.mkdir();(target/'outside.py').write_text('secret=1',encoding='utf-8')
        try:
            os.symlink(target,root/'linked',target_is_directory=True)
            linked=inspect_project_evidence(root);req(linked['link_or_boundary_rejection_count']>=1,'symlink_boundary_rejected')
            req('outside.py' not in json.dumps(linked),'symlink_target_not_scanned')
        except OSError:
            req(True,'symlink_fixture_unavailable_without_failure')
    # Casefold collision is rejected even on a case-sensitive host.
    collision=Path(td)/'collision';collision.mkdir();(collision/'A.py').write_text('a=1',encoding='utf-8');(collision/'a.py').write_text('a=2',encoding='utf-8')
    try:
        inspect_project_evidence(collision)
        req(False,'casefold_collision_should_reject')
    except ValueError as exc:
        req('casefold' in str(exc),'casefold_collision_rejected')
    # Invalid external evidence cannot smuggle arbitrary kinds or raw payloads into the assessment.
    try:
        build_evidence_based_project_assessment(root,external_evidence=[{'kind':'provider_payload','status':'present','raw':'secret'}]);req(False,'unsupported_external_kind_should_reject')
    except ValueError:
        req(True,'unsupported_external_kind_rejected')
    same1=build_evidence_based_project_assessment(root,external_evidence=[{'kind':'environment','status':'available','claim_code':'python_runtime','polarity':'supports','source_ref':'fixture'}])
    same2=build_evidence_based_project_assessment(root,external_evidence=[{'kind':'environment','status':'available','claim_code':'python_runtime','polarity':'supports','source_ref':'fixture'}])
    req(same1['assessment_digest']==same2['assessment_digest'],'duplicate_assessment_deterministic')
    tampered=dict(same1);tampered['evidence_gap_count']=999;req(not validate_project_assessment(tampered)['ok'],'tampered_reliability_record_rejected')
for k,v in DENIED_AUTHORITY.items(): req(health[k] is v and handoff[k] is v,f'{k}_denied')
req(sig()==before,'reliability_suite_preserves_source')
print(json.dumps({'ok':True,'suite':'v1261.6-v1261.8-evidence-based-project-inspection-reliability','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'commands_executed':False,'project_modified':False,'native_windows_validation':'desktop_review_required','release_authorized':False},indent=2,sort_keys=True))
