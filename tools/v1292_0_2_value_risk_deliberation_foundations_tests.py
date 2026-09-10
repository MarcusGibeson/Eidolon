from __future__ import annotations
import json,sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from value_risk_deliberation_foundations import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
def d(s):return sha256(s.encode()).hexdigest()
def a(name='a',**kw):return {'proposal_id':'p-'+name,'proposal_digest':d(name),'expected_value':kw.pop('expected_value',80),'risk':kw.pop('risk',30),'reversibility':kw.pop('reversibility',80),'cost':kw.pop('cost',30),'uncertainty':kw.pop('uncertainty',20),'urgency':kw.pop('urgency',60),**kw}
rows=normalize_alternatives([a('a'),a('a'),a('b')]);req(len(rows)==2,'dedupe');req(rows[0]['content_free'],'content_free')
s=alternative_score(normalize_alternatives([a()])[0]);req(not s['blocked'],'normal_viable');req(s['score']>0,'positive_score');req(all(s[k] is False for k in DENIED_AUTHORITY),'no_authority')
for raw,reason in [(a(evidence_fresh=False),'stale_evidence'),(a(dependency_blocked=True),'dependency_blocked'),(a(critical_risk=True),'critical_risk'),(a(irreversible=True,risk=70),'high_risk_irreversible'),(a(uncertainty=90),'uncertainty_too_high')]:
 x=alternative_score(normalize_alternatives([raw])[0]);req(x['blocked'] and reason in x['block_reasons'],reason)
low=alternative_score(normalize_alternatives([a(expected_value=20,risk=90,cost=90,uncertainty=80,reversibility=10,urgency=10)])[0]);req(low['score']<s['score'],'burden_reduces_score');req(ARCHITECTURE_LINEAGE['priority_selection']=='v1263' and ARCHITECTURE_LINEAGE['calibrated_uncertainty']=='v1282','lineage')
try:normalize_alternatives([a()|{'proposal_digest':'bad'}]);bad=False
except ValueError:bad=True
req(bad,'bad_identity')
print(json.dumps({'ok':True,'suite':'v1292.0-v1292.2-value-risk-deliberation-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
