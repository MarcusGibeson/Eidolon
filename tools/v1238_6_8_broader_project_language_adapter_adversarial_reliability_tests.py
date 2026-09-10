from __future__ import annotations
import json, tempfile, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
import broader_project_language_adapters as a
checks=[]
def check(v): checks.append(bool(v))
# Path, privacy, and secret-bearing inputs fail closed.
for paths,reason in [(['/etc/passwd'],'absolute'),(['../pom.xml'],'traversal'),(['.env','pom.xml'],'secret'),(['keys/private.pem','pom.xml'],'secret')]:
    row=a.prepare_broader_project_adapter_assessment('project_'+'e'*16,relative_paths=paths,runtime_root=tempfile.mkdtemp())
    check(row.get('ok') is False); check(reason in row.get('reason',''))
invalid_digest=a.prepare_broader_project_adapter_assessment('project_'+'f'*16,relative_paths=['pom.xml'],manifest_digests={'pom.xml':'nope'},runtime_root=tempfile.mkdtemp())
check(invalid_digest.get('ok') is False); check('invalid_manifest_digest' in invalid_digest.get('reason',''))
missing_marker=a.prepare_broader_project_adapter_assessment('project_'+'1'*16,relative_paths=['pom.xml'],manifest_digests={'build.gradle':'1'*64},runtime_root=tempfile.mkdtemp())
check(missing_marker.get('ok') is False); check('manifest_digest_without_inventory_marker' in missing_marker.get('reason',''))
# Mixed broader/existing families are ambiguous and cannot be accepted.
rt=tempfile.mkdtemp(prefix='eidolon-v1238-adv-')
mixed=a.prepare_broader_project_adapter_assessment('project_'+'2'*16,relative_paths=['pom.xml','package.json','src/App.java'],runtime_root=rt)
check(mixed.get('ok')); check(mixed.get('detection_state')=='adapter_ambiguous')
blocked=a.review_broader_project_adapter_assessment(mixed['assessment_id'],expected_assessment_digest=mixed['assessment_digest'],disposition='accept_adapter',runtime_root=rt)
check(blocked.get('ok') is False); check('selected_adapter_required' in blocked.get('reason',''))
# Stale digest, conflicting decisions, and blueprint review lineage fail closed.
rt=tempfile.mkdtemp(prefix='eidolon-v1238-stale-')
assessment=a.prepare_broader_project_adapter_assessment('project_'+'3'*16,relative_paths=['Cargo.toml','src/main.rs'],runtime_root=rt)
stale=a.review_broader_project_adapter_assessment(assessment['assessment_id'],expected_assessment_digest='0'*64,disposition='accept_adapter',runtime_root=rt)
check(stale.get('ok') is False); check('stale_assessment_digest' in stale.get('reason',''))
review=a.review_broader_project_adapter_assessment(assessment['assessment_id'],expected_assessment_digest=assessment['assessment_digest'],disposition='accept_adapter',runtime_root=rt)
check(review.get('ok'))
conflict=a.review_broader_project_adapter_assessment(assessment['assessment_id'],expected_assessment_digest=assessment['assessment_digest'],disposition='reject',runtime_root=rt)
check(conflict.get('ok') is False); check('different_disposition' in conflict.get('reason',''))
wrong=a.prepare_adapter_orchestration_blueprint(assessment['assessment_id'],expected_assessment_digest='0'*64,review_id=review['review_id'],expected_review_digest=review['review_digest'],runtime_root=rt)
check(wrong.get('ok') is False); check('stale_assessment_digest' in wrong.get('reason',''))
# Tamper persisted assessment and ensure closure.
path=Path(rt)/'development_campaigns'/'broader_project_adapter_assessments'/f"{assessment['assessment_id']}.json"
data=json.loads(path.read_text()); data['language']='tampered'; path.write_text(json.dumps(data))
tampered=a.load_broader_project_adapter_assessment(assessment['assessment_id'],runtime_root=rt)
check(tampered.get('ok') is False); check('tampered' in tampered.get('status',''))
# Unknown requested adapter and marker mismatch fail closed.
unknown=a.prepare_broader_project_adapter_assessment('project_'+'4'*16,relative_paths=['go.mod'],requested_adapter_id='java_maven',runtime_root=tempfile.mkdtemp())
check(unknown.get('ok')); check(unknown.get('detection_state')=='adapter_blocked'); check(unknown.get('detection_reason')=='requested_adapter_marker_mismatch')
unknown2=a.prepare_broader_project_adapter_assessment('project_'+'5'*16,relative_paths=['go.mod'],requested_adapter_id='not_real',runtime_root=tempfile.mkdtemp())
check(unknown2.get('ok')); check(unknown2.get('detection_state')=='adapter_blocked')
# Every returned success remains content-free and powerless.
for row in (mixed,assessment,review,unknown,unknown2):
    check(row.get('project_contents_read') is False); check(row.get('manifest_contents_read') is False); check(row.get('provider_contacted') is False); check(row.get('commands_executed') is False); check(row.get('tests_executed') is False); check(row.get('project_modified') is False); check(row.get('cognition_written') is False); check(row.get('automatic_continuation_created') is False); check(row.get('hidden_retry_created') is False)
    for k,e in a.AUTHORITY_FLAGS.items(): check(row.get(k) is e)
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True)); raise SystemExit(0 if all(checks) else 1)
