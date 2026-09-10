from __future__ import annotations
import json,sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from independent_improvement_proposals import generate_improvement_proposals,observations_from_product_quality
from independent_improvement_proposals_foundations import DENIED_AUTHORITY
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
def d(s):return sha256(s.encode()).hexdigest()
def o(kind,name,impact=70,**kw):return {'kind':kind,'issue_digest':d('issue-'+name),'evidence_digest':d('evidence-'+name),'relevance':kw.pop('relevance',80),'impact':impact,'confidence':kw.pop('confidence',80),'actionability':kw.pop('actionability',80),'novel':kw.pop('novel',True),'fresh':kw.pop('fresh',True),'private':kw.pop('private',False),**kw}
r=generate_improvement_proposals([o('defect','bug',95),o('maintainability','maint',55),o('todo','todo',99),o('aesthetic_preference','pretty',99),o('defect','stale',95,fresh=False),o('defect','dup',95,novel=False)])
req(r['proposal_count']==2,'only_material_actionable');req(r['suppressed_count']==4,'suppressed_count');req(r['proposals'][0]['kind']=='defect','impact_ranking');req(all(p['state']=='proposal_only' and p['requires_operator_selection'] for p in r['proposals']),'proposal_only');req(all(not p['creates_backlog_item'] and not p['executes_work'] for p in r['proposals']),'no_work_created');req(r['observations_do_not_imply_work'],'observations_not_work')
none=generate_improvement_proposals([o('todo','a',90),o('uncertainty','b',90),o('aesthetic_preference','c',90)]);req(none['nothing_worth_proposing'] and none['proposal_count']==0,'deliberate_no_proposal')
jud={'dimension_states':{'coherence':'pass','usability':'warn','accessibility':'fail','maintainability':'pass','completeness':'unknown','operator_readiness':'pass'},'scope_digest':d('scope'),'judgment_digest':d('judgment')};obs=observations_from_product_quality(jud);req({x['kind'] for x in obs}=={'usability','accessibility'},'quality_only_gaps');q=generate_improvement_proposals(obs);req(q['proposal_count']==2,'quality_gaps_proposed');req(q['proposals'][0]['kind']=='accessibility','failed_gap_outranks_warning');req(all(q[k] is False for k in DENIED_AUTHORITY),'no_authority')
print(json.dumps({'ok':True,'suite':'v1291.3-v1291.5-independent-improvement-proposals-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
