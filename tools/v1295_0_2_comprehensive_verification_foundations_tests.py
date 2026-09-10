from __future__ import annotations
import json,platform,sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from comprehensive_verification_foundations import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
def d(s):return sha256(s.encode()).hexdigest()
r=evidence_record('focused_tests',status='passed',source_tree_digest=d('s'),candidate_digest=d('c'),evidence_digest=d('e'),summary={'passed':4,'total':4});req(r['status']=='passed','record');req(r['content_free'],'content_free');req(all(r[k] is False for k in DENIED_AUTHORITY),'no_authority');req(len(EVIDENCE_DOMAINS)==11,'domains')
n=native_windows_pending_evidence(source_tree_digest=d('s'),candidate_digest=d('c'),platform_name=platform.system());req(n['domain']=='native_windows' and n['status'] in {'pending','unavailable'},'native_pending_here');req(not n['native_attested'],'not_attested')
try:evidence_record('native_windows',status='passed',source_tree_digest=d('s'),candidate_digest=d('c'),platform_name='linux',native_attested=False);bad=False
except ValueError:bad=True
req(bad,'false_native_pass_rejected')
w=evidence_record('native_windows',status='passed',source_tree_digest=d('s'),candidate_digest=d('c'),platform_name='windows',native_attested=True);req(w['status']=='passed' and w['native_attested'],'attested_windows_allowed')
try:evidence_record('focused_tests',status='passed',source_tree_digest=d('s'),candidate_digest=d('c'),fresh=False);bad2=False
except ValueError:bad2=True
req(bad2,'stale_pass_rejected');req(valid_digest(r['evidence_digest']),'evidence_digest');req(ARCHITECTURE_LINEAGE['hermetic_runtime']=='v1250.2' and ARCHITECTURE_LINEAGE['candidate_evaluation']=='v1294','lineage');req({'passed','failed','blocked','unavailable','pending'}==VALID_STATES,'states')
print(json.dumps({'ok':True,'suite':'v1295.0-v1295.2-comprehensive-verification-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
