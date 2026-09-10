from __future__ import annotations
"""Strictly read-only v1133.8 Internally Generated Goal Integration checkpoint."""
import hashlib, os
from pathlib import Path
from internally_generated_goal_outcome_lineage import build_internally_generated_goal_outcome_lineage_inspection
from internally_generated_goal_reliability_review import build_internally_generated_goal_reliability_review_inspection
CONTRACT_VERSION='v1133.8'
def _sig(root:Path):
 h=hashlib.sha256()
 if not root.exists(): return h.hexdigest()
 for p in sorted(x for x in root.rglob('*') if x.is_file() and '__pycache__' not in x.parts and x.suffix!='.pyc'):
  try: h.update(p.relative_to(root).as_posix().encode()); h.update(p.read_bytes())
  except OSError: pass
 return h.hexdigest()
def build_internally_generated_goal_integration_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root or (Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data')/'cognition')).resolve(); source=Path(source_root or Path(__file__).resolve().parents[1]).resolve(); rb=_sig(runtime); sb=_sig(source); lineage=build_internally_generated_goal_outcome_lineage_inspection(runtime); reliability=build_internally_generated_goal_reliability_review_inspection(runtime)
 checks=[('outcome_lineage',lineage.get('contract_version')=='v1133.6'),('exact_arbitration_lineage',all(x.get('arbitration_id') for x in lineage.get('recent_outcomes',[]))),('scope_digest_preserved',all('scope_digest' in x for x in lineage.get('recent_outcomes',[]))),('lifecycle_state',all('lifecycle_state' in x for x in lineage.get('recent_outcomes',[]))),('continuity_state',all('continuity_state' in x for x in lineage.get('recent_outcomes',[]))),('blocker_state',all('blocker_state' in x for x in lineage.get('recent_outcomes',[]))),('completion_state',all('completion_state' in x for x in lineage.get('recent_outcomes',[]))),('reliability_review',reliability.get('contract_version')=='v1133.7'),('false_pattern_suppression',all('false_pattern_suppressed' in x for x in reliability.get('reviews',[]))),('fixation_and_abandonment_review',all('accepted_count' in x and 'abandoned_count' in x for x in reliability.get('reviews',[]))),('visible_status',not reliability.get('visible_status',{}).get('raw_content_exposed')),('no_autonomous_activation',not lineage.get('authority_boundary',{}).get('can_activate_goal')),('authority_separation',not any(lineage.get(k) for k in ('provider_contacted','external_action_executed'))),('privacy',not lineage.get('raw_content_exposed') and not lineage.get('hidden_reasoning_exposed')),('desktop_pending',True)]
 return {'ok':all(v for _,v in checks),'contract_version':CONTRACT_VERSION,'checks':[{'id':k,'status':'pass' if v else 'fail'} for k,v in checks],'lineage':lineage,'reliability':reliability,'visible_status':reliability.get('visible_status',{}),'runtime_mutated':rb!=_sig(runtime),'source_modified':sb!=_sig(source),'raw_content_exposed':False,'evidence_text_exposed':False,'goal_text_exposed':False,'prompt_exposed':False,'provider_payload_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'message_sent':False,'notification_created':False,'approval_created':False,'authorization_created':False,'external_action_executed':False,'promotion_performed':False,'certification_performed':False,'desktop_verification':'pending'}
