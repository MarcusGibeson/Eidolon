from __future__ import annotations
"""Strictly read-only v1128.8 Reflection-Supported Revision Integration checkpoint."""
import hashlib, os
from pathlib import Path
from reflection_supported_revision_outcome_lineage import build_reflection_supported_revision_outcome_lineage_inspection
from reflection_supported_revision_reliability_review import build_reflection_supported_revision_reliability_review_inspection
from reflection_supported_revision_arbitration import build_reflection_supported_revision_arbitration_inspection
CONTRACT_VERSION='v1128.8'
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _sig(root):
 d=hashlib.sha256(); root=Path(root)
 if not root.exists(): return d.hexdigest()
 for p in sorted(x for x in root.rglob('*') if x.is_file() and '__pycache__' not in x.parts and x.suffix!='.pyc'): d.update(p.relative_to(root).as_posix().encode()); d.update(p.read_bytes())
 return d.hexdigest()
def build_reflection_supported_revision_integration_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root).resolve() if runtime_root else _root(); source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]; rb,sb=_sig(runtime),_sig(source); lineage=build_reflection_supported_revision_outcome_lineage_inspection(runtime); reliability=build_reflection_supported_revision_reliability_review_inspection(runtime); arbitration=build_reflection_supported_revision_arbitration_inspection(runtime)
 checks=[lineage.get('ok'),reliability.get('ok'),arbitration.get('ok'),lineage.get('contract_version')=='v1128.6',reliability.get('contract_version')=='v1128.7',arbitration.get('contract_version')=='v1128.4',not lineage.get('raw_content_exposed'),not reliability.get('raw_content_exposed'),not lineage.get('hidden_reasoning_exposed'),not reliability.get('hidden_reasoning_exposed'),not lineage.get('revision_applied'),not lineage.get('target_revised'),not reliability.get('revision_applied'),not reliability.get('target_revised'),not lineage.get('provider_contacted'),not lineage.get('message_sent'),not lineage.get('external_action_executed'),rb==_sig(runtime) and sb==_sig(source)]
 rows=[{'check':f'check_{i+1}','status':'pass' if v else 'fail','passed':bool(v)} for i,v in enumerate(checks)]; passed=sum(bool(x) for x in checks)
 return {'ok':passed==18,'contract_version':CONTRACT_VERSION,'status':'ready_for_desktop_verification' if passed==18 else 'degraded','headline':f'v1128.8 Reflection-Supported Revision Integration and Reliability: {passed}/18 checks passed','checks':rows,'passed':passed,'total':18,'summary':{'revision_outcome_count':lineage.get('outcome_count',0),'revision_review_count':reliability.get('review_count',0)},'lineage':lineage,'reliability':reliability,'arbitration':arbitration,'raw_content_exposed':False,'hidden_reasoning_exposed':False,'revision_applied':False,'target_revised':False,'provider_contacted':False,'message_sent':False,'external_action_executed':False,'runtime_mutated':rb!=_sig(runtime),'source_modified':sb!=_sig(source),'desktop_verification_pending':True}
