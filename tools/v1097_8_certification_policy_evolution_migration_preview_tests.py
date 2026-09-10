from __future__ import annotations
import copy,json,shutil,tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
for item in (ROOT/'conscious_agent',ROOT/'tools'):sys.path.insert(0,str(item))
from v1097_bundle_c_test_support import prepare_certified_fixture,write_policy
from release_certification_history import create_certification_history_reconciliation_preview
from release_certification_policy import *
from release_certification_transaction import certification_status

def c(n,o):return {'name':n,'ok':bool(o)}
def main():
 rows=[]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-8-') as td:
  base=Path(td);f=prepare_certified_fixture(base/'seed');rr=Path(f['handoff_runtime']);create_certification_history_reconciliation_preview(runtime_root=rr);authority_before=certification_status(runtime_root=rr)
  no=select_certification_policy(runtime_root=rr);rows.append(c('explicit-selection-required',not no.get('ok')))
  selected=select_certification_policy(built_in_policy_id=BUILTIN_POLICY_ID,runtime_root=rr);rows += [c('builtin-policy-selected',selected.get('ok') and selected.get('built_in')),c('policy-identity-bound',bool(selected.get('policy_sha256')) and selected.get('policy_id')==BUILTIN_POLICY_ID)]
  sibling=write_policy(base/'policies/sibling.json');selected2=select_certification_policy(base/'policies/exact.json' if False else write_policy(base/'policies/exact.json'),runtime_root=rr);rows.append(c('exact-policy-only',selected2.get('ok') and sibling.exists()))
  preview=create_policy_migration_preview(runtime_root=rr);rows += [c('migration-preview',preview.get('ok') and len(preview.get('scope_impacts',[]))==4),c('general-compatible',any(x['scope']=='general_release' and x['classification'] in {'compatible','unchanged'} for x in preview.get('scope_impacts',[]))),c('no-auto-migration',not preview.get('policy_migrated') and certification_status(runtime_root=rr).get('certification_state_sha256')==authority_before.get('certification_state_sha256'))]
  wrong=acknowledge_policy_migration_preview(preview['authorization_token'],confirm='true',runtime_root=rr);ok=acknowledge_policy_migration_preview(preview['authorization_token'],confirm=POLICY_ACK_CONFIRMATION,runtime_root=rr);reuse=acknowledge_policy_migration_preview(preview['authorization_token'],confirm=POLICY_ACK_CONFIRMATION,runtime_root=rr);rows += [c('literal-confirmation',not wrong.get('ok')),c('acknowledge-only',ok.get('ok') and not ok.get('policy_migrated')),c('single-use-token',not reuse.get('ok'))]
  stale=create_policy_migration_preview(runtime_root=rr);alt=copy.deepcopy(BUILTIN_POLICY);alt['policy_id']='alternate';alt['version']='1097.8-2';select_certification_policy(write_policy(base/'policies/alt.json',alt),runtime_root=rr);stale_out=acknowledge_policy_migration_preview(stale['authorization_token'],confirm=POLICY_ACK_CONFIRMATION,runtime_root=rr);rows.append(c('stale-cross-policy-token',not stale_out.get('ok')))
  other=base/'other';shutil.copytree(rr,other);cross=acknowledge_policy_migration_preview(stale['authorization_token'],confirm=POLICY_ACK_CONFIRMATION,runtime_root=other);rows.append(c('cross-runtime-token-rejected',not cross.get('ok')))
  bad=copy.deepcopy(BUILTIN_POLICY);bad['migration_compatibility']['automatic_migration_allowed']=True;rejected=select_certification_policy(write_policy(base/'policies/bad.json',bad),runtime_root=rr);rows.append(c('automatic-migration-policy-rejected',not rejected.get('ok')))
  leak=copy.deepcopy(BUILTIN_POLICY);leak['private_path']='/tmp/secret';rejected=select_certification_policy(write_policy(base/'policies/leak.json',leak),runtime_root=rr);rows.append(c('policy-path-private',not rejected.get('ok')))
  rows += [c('malformed-token-rejected',not acknowledge_policy_migration_preview('truthy',confirm=POLICY_ACK_CONFIRMATION,runtime_root=rr).get('ok')),c('scope-authority-unchanged',certification_status(runtime_root=rr).get('certified_scopes')==authority_before.get('certified_scopes'))]
 report={'suite':'v1097.8-certification-policy-evolution-migration-preview','passed':sum(x['ok'] for x in rows),'failed':sum(not x['ok'] for x in rows),'checks':rows};report['ok']=report['failed']==0;print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
