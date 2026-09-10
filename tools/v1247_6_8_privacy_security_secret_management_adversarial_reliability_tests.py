from __future__ import annotations
import hashlib,json,sys,tempfile,zipfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from privacy_security_secret_management_audit import *
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest();c=[];ck=lambda v:c.append(bool(v))
finding=dict(finding_code='secret_reference',category='credential',classification='unverified_finding',location_digest=h('loc'),evidence_digest=h('ev'),confidence=.5,remediation_code='operator_review',remediated=False)
base=dict(project_id='project_alpha',audit_scope_code='full_stack',source_inventory_digest=h('inv'),package_digest=h('pkg'),trust_boundary_digests=[h('t')],data_flow_digests=[h('d')],retention_policy_digest=h('r'),findings=[finding])
with tempfile.TemporaryDirectory() as rt:
    audit=prepare_privacy_security_audit(runtime_root=rt,**base);path=Path(rt)/'development_campaigns'/'privacy_security_audits'/f"{audit['audit_id']}.json";data=json.loads(path.read_text());data['finding_count']=999;path.write_text(json.dumps(data));loaded=load_privacy_security_audit(audit['audit_id'],runtime_root=rt);ck(not loaded['ok']);ck(loaded['status']=='privacy_security_audit_tampered')
with tempfile.TemporaryDirectory() as rt:
    audit=prepare_privacy_security_audit(runtime_root=rt,**base);bad=review_privacy_security_audit(audit['audit_id'],expected_audit_digest=h('wrong'),disposition='accept_findings',exact_phrase='wrong',runtime_root=rt);ck(not bad['ok']);ck(not bad['secret_value_disclosure_authorized'])
with tempfile.TemporaryDirectory() as rt:
    audit=prepare_privacy_security_audit(runtime_root=rt,**base);phrase=f"review privacy security audit hold for audit {audit['audit_id']} digest {audit['privacy_security_audit_digest']}";review=review_privacy_security_audit(audit['audit_id'],expected_audit_digest=audit['privacy_security_audit_digest'],disposition='hold',exact_phrase=phrase,runtime_root=rt);proposal=prepare_secret_management_remediation_proposal(review['review_id'],expected_audit_review_digest=review['privacy_security_audit_review_digest'],action_rows=[{'finding_id':audit['findings'][0]['finding_id'],'action':'rotate'}],verification_plan_digest=h('v'),rollback_plan_digest=h('b'),runtime_root=rt);ck(not proposal['ok']);ck(proposal['status']=='secret_management_remediation_proposal_blocked')
with tempfile.TemporaryDirectory() as td:
    root=Path(td);(root/'src').mkdir();(root/'src'/'bad.py').write_text('password="realistic-secret-value"\n');scan=scan_source_tree_for_secret_findings(root);ck(not scan['ok']);ck(scan['classification_counts']['likely_secret']==1);ck(scan['confirmed_or_likely_count']==1);ck(all('password' not in json.dumps(x) for x in scan['findings']))
with tempfile.TemporaryDirectory() as td:
    root=Path(td);(root/'.gitignore').write_text('data/\n');archive=root/'bad.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('Eidolon/data/settings.json','{}')
    package=scan_source_package_privacy(root,zip_path=archive);ck(not package['ok']);ck(package['zip_forbidden_count']>=1);ck(not package['authorizes_packaging']);ck(all(len(x)==64 for x in package['forbidden_entry_digests']))
attacks=[dict(base,project_id='project_../escape'),dict(base,audit_scope_code='private content'),dict(base,findings=[dict(finding,matched_text='x')]),dict(base,findings=[dict(finding,classification='confirmed_secret',remediation_code='rotate',evidence_digest='bad')]),dict(base,previous_audit_id='privacy_security_audit_'+'a'*24,generation=2),dict(base,retention_policy_digest='0'*63)]
for args in attacks:
    with tempfile.TemporaryDirectory() as rt:
        row=prepare_privacy_security_audit(runtime_root=rt,**args);ck(not row['ok']);ck(not row['credential_rotation_authorized']);ck(not row['file_deletion_authorized']);ck(not row['package_mutation_authorized'])
for k,e in AUTHORITY_FLAGS.items():ck(build_privacy_security_secret_management_contract().get(k) is e)
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
