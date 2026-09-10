from __future__ import annotations
import copy,json,sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from independent_improvement_proposals import generate_improvement_proposals
from independent_improvement_proposals_foundations import DENIED_AUTHORITY
from independent_improvement_proposals_reliability import assess_improvement_proposal_reliability
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
def d(s):return sha256(s.encode()).hexdigest()
o={'kind':'defect','issue_digest':d('i'),'evidence_digest':d('e'),'relevance':90,'impact':90,'confidence':90,'actionability':90};good=generate_improvement_proposals([o]);r=assess_improvement_proposal_reliability([good]);req(r['ok'],'good')
def catch(mut,t):
 x=copy.deepcopy(good);mut(x);z=assess_improvement_proposal_reliability([x]);return any(t in v for v in z['violations'])
req(catch(lambda x:x.__setitem__('observations_do_not_imply_work',False),'observation_work_conflation'),'work_conflation')
req(catch(lambda x:x['proposals'][0].__setitem__('state','approved_work'),'proposal_became_work'),'state_escalation')
req(catch(lambda x:x['proposals'][0].__setitem__('executes_work',True),'proposal_became_work'),'execution_escalation')
req(catch(lambda x:x['proposals'][0].__setitem__('creates_backlog_item',True),'proposal_became_work'),'backlog_escalation')
req(catch(lambda x:x['proposals'][0].__setitem__('requires_operator_selection',False),'operator_selection_missing'),'operator_selection')
req(catch(lambda x:x['proposals'][0].__setitem__('project_mutation_authorized',True),'proposal_authority_expansion'),'proposal_authority')
req(catch(lambda x:x.__setitem__('release_authorized',True),'result_authority_expansion'),'result_authority')
req(r['content_free'] and r['read_only'],'readonly');req(all(r[k] is False for k in DENIED_AUTHORITY),'no_authority')
print(json.dumps({'ok':True,'suite':'v1291.6-v1291.8-independent-improvement-proposals-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
