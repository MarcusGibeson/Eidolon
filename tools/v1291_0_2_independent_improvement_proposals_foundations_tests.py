from __future__ import annotations
import json,sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from independent_improvement_proposals_foundations import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
def d(s):return sha256(s.encode()).hexdigest()
def obs(kind='defect',name='x',**kw):return {'kind':kind,'issue_digest':d('i'+name),'evidence_digest':d('e'+name),'relevance':kw.pop('relevance',80),'impact':kw.pop('impact',80),'confidence':kw.pop('confidence',80),'actionability':kw.pop('actionability',80),**kw}
rows=normalize_observations([obs(name='a'),obs(name='a'),obs('todo','b')]);req(len(rows)==2,'dedupe');req(all(x['content_free'] for x in rows),'content_free')
req(proposal_eligibility(normalize_observations([obs()])[0])['eligible'],'strong_eligible')
for raw,label in [(obs('todo'),'todo'),(obs('uncertainty'),'uncertainty'),(obs('aesthetic_preference'),'aesthetic'),(obs(fresh=False),'stale'),(obs(novel=False),'duplicate'),(obs(private=True),'private'),(obs(relevance=10),'irrelevant'),(obs(impact=10),'low_value'),(obs(confidence=10),'weak_evidence'),(obs(actionability=10),'not_actionable')]:req(not proposal_eligibility(normalize_observations([raw])[0])['eligible'],label+'_suppressed')
try:normalize_observations([obs()|{'evidence_digest':'bad'}]);bad=False
except ValueError:bad=True
req(bad,'bad_digest');g=proposal_eligibility(normalize_observations([obs()])[0]);req(g['proposal_is_work'] is False,'eligibility_not_work');req(all(g[k] is False for k in DENIED_AUTHORITY),'no_authority')
print(json.dumps({'ok':True,'suite':'v1291.0-v1291.2-independent-improvement-proposals-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
