from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from privacy_security_secret_management_audit import *
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest();c=[];ck=lambda v:c.append(bool(v))
reg=privacy_security_secret_management_registry();contract=build_privacy_security_secret_management_contract()
for v in (reg['ok'],reg['inspection_only'],reg['redacted_findings_only'],len(reg['finding_classifications'])==8,len(reg['secret_categories'])>=12,len(reg['remediation_actions'])==6,contract['ok'],contract['threat_model_and_data_classification'],contract['source_and_archive_scanning'],contract['no_secret_value_disclosure'],contract['no_automatic_remediation']):ck(v)
for k,e in AUTHORITY_FLAGS.items():ck(reg.get(k) is e and contract.get(k) is e)
with tempfile.TemporaryDirectory() as td:
    root=Path(td);(root/'tools').mkdir();(root/'tools'/'fixture.py').write_text('token="ghp_123456789012345678901234567890"\n');(root/'safe.py').write_text('PUBLIC_ID="abc"\n')
    scan=scan_source_tree_for_secret_findings(root)
    for v in (scan['ok'],scan['finding_count']==1,scan['classification_counts']['synthetic_test_canary']==1,scan['confirmed_or_likely_count']==0,not scan['secret_values_returned'],not scan['matched_text_returned'],all('matched_text' not in x and 'path' not in x for x in scan['findings'])):ck(v)
actual=scan_source_tree_for_secret_findings(R)
for v in (actual['ok'],actual['confirmed_or_likely_count']==0,actual['scanned_file_count']>2000,bool(actual['scan_digest'])):ck(v)
classes=sorted(FINDING_CLASSIFICATIONS)
findings=[dict(finding_code=f'f{i}',category=sorted(SECRET_CATEGORIES)[i%len(SECRET_CATEGORIES)],classification=x,location_digest=h(f'l{i}'),evidence_digest=h(f'e{i}'),confidence=.8,remediation_code='operator_review',remediated=x=='remediated_finding') for i,x in enumerate(classes)]
base=dict(project_id='project_alpha',audit_scope_code='full_stack',source_inventory_digest=h('inv'),package_digest=h('pkg'),trust_boundary_digests=[h('t1'),h('t2')],data_flow_digests=[h('d1')],retention_policy_digest=h('ret'),findings=findings)
with tempfile.TemporaryDirectory() as rt:
    row=prepare_privacy_security_audit(runtime_root=rt,**base);same=prepare_privacy_security_audit(runtime_root=rt,**dict(base,trust_boundary_digests=list(reversed(base['trust_boundary_digests']))))
    for v in (row['ok'],row['status']=='privacy_security_audit_prepared',row['finding_count']==8,row['classification_counts']['confirmed_secret']==1,row['release_blocked_by_secret_findings'],same['audit_id']==row['audit_id'],same['privacy_security_audit_digest']==row['privacy_security_audit_digest'],load_privacy_security_audit(row['audit_id'],runtime_root=rt)['ok']):ck(v)
    public=public_privacy_security_audits(runtime_root=rt);dash=privacy_security_audit_dashboard_record(runtime_root=rt);page=render_privacy_security_audit_dashboard_html(runtime_root=rt)
    for v in (public['count']==1,dash['read_only'],dash['get_only'],dash['audit_count']==1,'Secret values and matched text are never displayed' in page,not dash['secret_values_returned'],not dash['matched_text_returned']):ck(v)
    for k,e in AUTHORITY_FLAGS.items():ck(row.get(k) is e and dash.get(k) is e)
invalid=[dict(base,project_id='bad'),dict(base,trust_boundary_digests=[]),dict(base,data_flow_digests=[]),dict(base,findings=[]),dict(base,generation=2),dict(base,source_inventory_digest='bad'),dict(base,findings=[dict(findings[0],secret_value='do-not-store')])]
for args in invalid:
    with tempfile.TemporaryDirectory() as rt:
        row=prepare_privacy_security_audit(runtime_root=rt,**args);ck(not row['ok']);ck(row['status']=='privacy_security_audit_blocked')
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
