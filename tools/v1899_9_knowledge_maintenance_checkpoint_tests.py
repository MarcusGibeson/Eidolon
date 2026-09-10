from __future__ import annotations
import json,sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from knowledge_freshness_maintenance import *
checks=[]
def req(v,n): checks.append(n); assert v,n
now=datetime(2026,8,22,tzinfo=timezone.utc)
rows=[
 {'id':'stable','type':'definition','created_at':(now-timedelta(days=500)).isoformat()},
 {'id':'ver','type':'library_version','version':'1','created_at':(now-timedelta(days=300)).isoformat()},
 {'id':'time','type':'current_price','time_sensitive':True,'created_at':(now-timedelta(days=10)).isoformat()},
 {'id':'local','type':'current_config','runtime_local':True,'created_at':(now-timedelta(days=2)).isoformat()},
 {'id':'ext','type':'research_fact','external_verification_required':True,'created_at':(now-timedelta(days=100)).isoformat()},
]
classes={classify_knowledge_freshness(r) for r in rows}
for cls in FRESHNESS_CLASSES: req(cls in classes,'class_'+cls)
out=inspect_knowledge_freshness(rows,now=now)
req(out['refresh_candidate_count']==4,'four_stale_dynamic_items')
req(out['external_browsing_performed'] is False and out['refresh_claimed_complete'] is False,'inspection_not_refresh')
local=next(c for c in out['refresh_candidates'] if c['freshness_class']=='local_runtime')
prop=build_refresh_proposal(local)
req(prop['operator_review_required_for_private_runtime'] is True,'local_runtime_requires_operator')
req(prop['browse_authorized'] is False and prop['provider_contact_authorized'] is False,'proposal_non_authorizing')
ext=next(c for c in out['refresh_candidates'] if c['freshness_class']=='externally_verifiable')
p2=build_refresh_proposal(ext)
evidence=[
 {'id':'good','source_type':'external_source','source_quality':'official','published_at':now.isoformat(),'citation':'official-doc'},
 {'id':'bad','source_type':'assistant','source_quality':'high','published_at':now.isoformat(),'citation':'generated'},
 {'id':'private','source_type':'external_source','source_quality':'official','published_at':now.isoformat(),'private':True},
]
a=assess_refresh_evidence(p2,evidence,now=now)
req(a['sufficient_for_review'] is True and a['current_evidence_count']==1,'quality_current_evidence_accepted')
req(a['rejected_generated_count']==1 and a['rejected_private_count']==1,'generated_private_rejected')
req(a['refresh_completed'] is False and a['generated_prose_is_evidence'] is False,'review_not_false_completion')
print(json.dumps({'suite':'v1899.9-knowledge-maintenance','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
