from __future__ import annotations
"""Strictly read-only v1131.8 Read-Only Perception Integration checkpoint."""
import hashlib, os
from pathlib import Path
from read_only_perception_outcome_lineage import build_read_only_perception_outcome_lineage_inspection
from read_only_perception_reliability_review import build_read_only_perception_reliability_review_inspection
CONTRACT_VERSION='v1131.8'
def _sig(root:Path):
 h=hashlib.sha256()
 if not root.exists():return h.hexdigest()
 for p in sorted(x for x in root.rglob('*') if x.is_file() and '__pycache__' not in x.parts and x.suffix!='.pyc'):
  try:h.update(p.relative_to(root).as_posix().encode());h.update(p.read_bytes())
  except OSError:pass
 return h.hexdigest()
def build_read_only_perception_integration_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root or (Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data')/'cognition')).resolve();source=Path(source_root or Path(__file__).resolve().parents[1]).resolve();rb=_sig(runtime);sb=_sig(source);lineage=build_read_only_perception_outcome_lineage_inspection(runtime);reliability=build_read_only_perception_reliability_review_inspection(runtime)
 checks=[('outcome_lineage',lineage.get('contract_version')=='v1131.6'),('perception_continuity',all('continuity_state' in x for x in lineage.get('recent_outcomes',[]))),('scope_digest_preserved',all('scope_digest' in x for x in lineage.get('recent_outcomes',[]))),('freshness_lineage',all('observation_freshness' in x for x in lineage.get('recent_outcomes',[]))),('pattern_review',reliability.get('contract_version')=='v1131.7'),('false_pattern_suppression',all('false_pattern_suppressed' in x for x in reliability.get('reviews',[]))),('failure_change_reliability',all('selected_count' in x for x in reliability.get('reviews',[]))),('visible_status',not reliability.get('visible_status',{}).get('raw_content_exposed')),('no_raw_read_or_mutation',not lineage.get('raw_file_content_exposed') and not lineage.get('filesystem_modified')),('authority_separation',not any(lineage.get(k) for k in ('browser_contacted','provider_contacted','message_sent','notification_created','external_action_executed'))),('privacy',not lineage.get('raw_event_payload_exposed') and not lineage.get('hidden_reasoning_exposed')),('desktop_pending',True)]
 return {'ok':all(v for _,v in checks),'contract_version':CONTRACT_VERSION,'checks':[{'id':k,'status':'pass' if v else 'fail'} for k,v in checks],'lineage':lineage,'reliability':reliability,'visible_status':reliability.get('visible_status',{}),'runtime_mutated':rb!=_sig(runtime),'source_modified':sb!=_sig(source),'raw_file_content_exposed':False,'raw_event_payload_exposed':False,'message_text_exposed':False,'prompt_exposed':False,'provider_payload_exposed':False,'hidden_reasoning_exposed':False,'filesystem_modified':False,'browser_contacted':False,'provider_contacted':False,'message_sent':False,'notification_created':False,'approval_created':False,'authorization_created':False,'external_action_executed':False,'promotion_performed':False,'certification_performed':False,'desktop_verification':'pending'}
