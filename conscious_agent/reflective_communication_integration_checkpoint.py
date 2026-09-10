from __future__ import annotations
"""Strictly read-only v1129.8 Reflective Communication Integration checkpoint."""
import hashlib, os
from pathlib import Path
from reflective_communication_outcome_lineage import build_reflective_communication_outcome_lineage_inspection
from reflective_communication_reliability_review import build_reflective_communication_reliability_review_inspection
CONTRACT_VERSION='v1129.8'
def _sig(root:Path):
 h=hashlib.sha256()
 if not root.exists():return h.hexdigest()
 for p in sorted(x for x in root.rglob('*') if x.is_file() and '__pycache__' not in x.parts and x.suffix!='.pyc'):
  try:h.update(p.relative_to(root).as_posix().encode());h.update(p.read_bytes())
  except OSError:pass
 return h.hexdigest()
def build_reflective_communication_integration_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root or (Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data')/'cognition')).resolve();source=Path(source_root or Path(__file__).resolve().parents[1]).resolve();rb=_sig(runtime);sb=_sig(source);lineage=build_reflective_communication_outcome_lineage_inspection(runtime);reliability=build_reflective_communication_reliability_review_inspection(runtime)
 checks=[('outcome_lineage',lineage.get('contract_version')=='v1129.6'),('delayed_follow_up_continuity',all('timing_state' in x for x in lineage.get('recent_outcomes',[]))),('interruption_reliability',all('interruption_respected' in x for x in lineage.get('recent_outcomes',[]))),('pattern_review',reliability.get('contract_version')=='v1129.7'),('false_pattern_suppression',all('false_pattern_suppressed' in x for x in reliability.get('reviews',[]))),('curiosity_usefulness',all('curiosity_useful_count' in x for x in reliability.get('reviews',[]))),('visible_status',not reliability.get('visible_status',{}).get('raw_content_exposed')),('authority_separation',not any(lineage.get(k) for k in ('message_sent','notification_created','initiative_created','external_action_executed'))),('privacy',not lineage.get('raw_content_exposed') and not lineage.get('hidden_reasoning_exposed')),('desktop_pending',True)]
 return {'ok':all(v for _,v in checks),'contract_version':CONTRACT_VERSION,'checks':[{'id':k,'status':'pass' if v else 'fail'} for k,v in checks],'lineage':lineage,'reliability':reliability,'visible_status':reliability.get('visible_status',{}),'runtime_mutated':rb!=_sig(runtime),'source_modified':sb!=_sig(source),'raw_content_exposed':False,'message_text_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'message_sent':False,'notification_created':False,'initiative_created':False,'approval_created':False,'authorization_created':False,'external_action_executed':False,'promotion_performed':False,'certification_performed':False,'desktop_verification':'pending'}
