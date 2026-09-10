from __future__ import annotations
import json,platform,sys,tempfile,zipfile
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from comprehensive_verification_foundations import *
from comprehensive_verification import combine_verification_evidence,evidence_from_suite
from hermetic_verification_runtime import copy_clean_source_snapshot,source_signature
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
def d(s):return sha256(s.encode()).hexdigest()
# Exercise retained clean-snapshot/immutability behavior on a disposable source.
tmp=Path(tempfile.mkdtemp(prefix='eidolon-v1295-'));src=tmp/'src';snap=tmp/'snap';src.mkdir();(src/'a.py').write_text('x=1\n');(src/'b.txt').write_text('ok\n');before=source_signature(src);cp=copy_clean_source_snapshot(source_root=src,snapshot_root=snap);after=source_signature(src);req(cp['ok'] and before==after and cp['source_signature']['tree_digest']==cp['snapshot_signature']['tree_digest'] and cp['source_signature']['file_count']==cp['snapshot_signature']['file_count'],'clean_snapshot_immutable')
# Exercise deterministic package/fresh-extract parity on the same disposable source.
zp=tmp/'c.zip'
with zipfile.ZipFile(zp,'w',compression=zipfile.ZIP_DEFLATED) as z:
 for p in sorted(src.rglob('*')):
  if p.is_file():z.writestr('Eidolon/'+p.relative_to(src).as_posix(),p.read_bytes())
fresh=tmp/'fresh';fresh.mkdir();zipfile.ZipFile(zp).extractall(fresh);req((fresh/'Eidolon/a.py').read_bytes()==(src/'a.py').read_bytes() and (fresh/'Eidolon/b.txt').read_bytes()==(src/'b.txt').read_bytes(),'fresh_parity')
s=d('source');c=d('candidate')
passed=[]
for domain in EVIDENCE_DOMAINS:
 if domain=='native_windows':continue
 passed.append(evidence_record(domain,status='passed',source_tree_digest=s,candidate_digest=c,evidence_digest=d(domain),summary={'verified':True}))
portable=combine_verification_evidence(passed+[native_windows_pending_evidence(source_tree_digest=s,candidate_digest=c,platform_name=platform.system())]);req(not portable['ok'] and portable['status']=='portable_verification_complete_native_pending','native_pending_not_pass');req(portable['portable_evidence_complete'] and not portable['native_windows_passed'],'portable_complete')
win=evidence_record('native_windows',status='passed',source_tree_digest=s,candidate_digest=c,evidence_digest=d('win'),platform_name='windows',native_attested=True)
full=combine_verification_evidence(passed+[win]);req(full['ok'] and full['status']=='comprehensive_verification_passed','full_with_attested_native');req(all(x=='passed' for x in full['domain_states'].values()),'all_domains')
fail=list(passed);fail[0]=evidence_record(fail[0]['domain'],status='failed',source_tree_digest=s,candidate_digest=c,evidence_digest=d('fail'));fr=combine_verification_evidence(fail+[win]);req(not fr['ok'] and fr['status']=='verification_failed','failure_propagates')
mismatch=list(passed);mismatch[0]=evidence_record(mismatch[0]['domain'],status='passed',source_tree_digest=d('other'),candidate_digest=c,evidence_digest=d('m'));mr=combine_verification_evidence(mismatch+[win]);req(mr['status']=='verification_integrity_blocked' and 'source_tree_identity_mismatch' in mr['integrity_violations'],'identity_mismatch')
missing=combine_verification_evidence(passed);req(not missing['ok'] and any('native_windows' in x for x in missing['integrity_violations']),'missing_native')
suite=evidence_from_suite(domain='focused_tests',passed=9,total=9,source_tree_digest=s,candidate_digest=c,evidence_digest=d('suite'));req(suite['status']=='passed' and suite['summary']['all_passed'],'suite_bridge');req(all(full[k] is False for k in DENIED_AUTHORITY),'no_authority')
print(json.dumps({'ok':True,'suite':'v1295.3-v1295.5-comprehensive-verification-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
