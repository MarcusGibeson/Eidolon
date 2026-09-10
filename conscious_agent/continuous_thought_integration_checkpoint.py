from __future__ import annotations
"""Strictly read-only v1127.8 Continuous Thought Integration and Reliability checkpoint."""
import hashlib, os
from pathlib import Path
from thought_thread_outcome_lineage import build_thought_thread_outcome_lineage_inspection
from thought_thread_reliability_review import build_thought_thread_reliability_review_inspection
from thought_thread_arbitration import build_thought_thread_arbitration_inspection
CONTRACT_VERSION='v1127.8'
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _sig(root):
 d=hashlib.sha256(); root=Path(root)
 if not root.exists(): return d.hexdigest()
 for p in sorted(x for x in root.rglob('*') if x.is_file() and '__pycache__' not in x.parts and x.suffix!='.pyc'): d.update(p.relative_to(root).as_posix().encode()); d.update(p.read_bytes())
 return d.hexdigest()
def build_continuous_thought_integration_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root).resolve() if runtime_root else _root(); source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]; rb,sb=_sig(runtime),_sig(source); lineage=build_thought_thread_outcome_lineage_inspection(runtime); reliability=build_thought_thread_reliability_review_inspection(runtime); arbitration=build_thought_thread_arbitration_inspection(runtime)
 checks=[lineage.get('ok'),reliability.get('ok'),arbitration.get('ok'),lineage.get('contract_version')=='v1127.6',reliability.get('contract_version')=='v1127.7',arbitration.get('contract_version')=='v1127.4',not lineage.get('raw_content_exposed'),not reliability.get('raw_content_exposed'),not lineage.get('hidden_reasoning_exposed'),not reliability.get('hidden_reasoning_exposed'),not lineage.get('provider_contacted'),not lineage.get('reflection_created'),not lineage.get('belief_updated'),not lineage.get('goal_updated'),not lineage.get('self_model_updated'),not lineage.get('message_sent'),not lineage.get('external_action_executed'),rb==_sig(runtime) and sb==_sig(source)]
 rows=[{'check':f'check_{i+1}','status':'pass' if v else 'fail','passed':bool(v)} for i,v in enumerate(checks)]; passed=sum(bool(x) for x in checks)
 return {'ok':passed==18,'contract_version':CONTRACT_VERSION,'status':'ready_for_desktop_verification' if passed==18 else 'degraded','headline':f'v1127.8 Continuous Thought Integration and Reliability: {passed}/18 checks passed','checks':rows,'passed':passed,'total':18,'summary':{'thread_outcome_count':lineage.get('outcome_count',0),'thread_review_count':reliability.get('review_count',0)},'lineage':lineage,'reliability':reliability,'arbitration':arbitration,'raw_content_exposed':False,'hidden_reasoning_exposed':False,'provider_contacted':False,'reflection_created':False,'belief_updated':False,'goal_updated':False,'self_model_updated':False,'message_sent':False,'initiative_created':False,'external_action_executed':False,'runtime_mutated':rb!=_sig(runtime),'source_modified':sb!=_sig(source),'desktop_verification_pending':True}
