from __future__ import annotations
import copy,json,sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from comprehensive_verification_foundations import *
from comprehensive_verification import combine_verification_evidence
from comprehensive_verification_reliability import assess_comprehensive_verification_reliability
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
def d(s):return sha256(s.encode()).hexdigest()
s=d('s');c=d('c');rows=[]
for domain in EVIDENCE_DOMAINS:
 rows.append(evidence_record(domain,status='passed',source_tree_digest=s,candidate_digest=c,evidence_digest=d(domain),platform_name='windows' if domain=='native_windows' else '',native_attested=domain=='native_windows'))
r=combine_verification_evidence(rows);req(r['ok'],'good');req(assess_comprehensive_verification_reliability([r])['ok'],'reliable')
def m(fn):
 x=copy.deepcopy(r);fn(x);return assess_comprehensive_verification_reliability([x])['violations']
req(any('authority' in v for v in m(lambda x:x.__setitem__('release_authorized',True))),'authority')
req(any('without_native' in v for v in m(lambda x:x.__setitem__('native_windows_passed',False))),'native_false_pass')
req(any('missing_or_nonpassing' in v for v in m(lambda x:x['domain_states'].__setitem__('privacy_security','pending'))),'domain_false_pass')
req(any('missing_evidence' in v for v in m(lambda x:x.__setitem__('missing_native_is_pass',True))),'missing_promoted')
req(any('release_authority' in v for v in m(lambda x:x.__setitem__('verification_is_release_authority',True))),'release_conflation')
req(any('invalid_verification_digest' in v for v in m(lambda x:x.__setitem__('verification_digest','bad'))),'digest')
req(any('integrity_violation' in v for v in m(lambda x:x.__setitem__('integrity_violations',['bad']))),'integrity')
b=assess_comprehensive_verification_reliability([r,r]);req(b['ok'] and b['result_count']==2,'batch');req(b['native_windows_execution_still_external_to_this_read_only_model'],'native_external');req(all(b[k] is False for k in DENIED_AUTHORITY),'no_authority')
print(json.dumps({'ok':True,'suite':'v1295.6-v1295.8-comprehensive-verification-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
