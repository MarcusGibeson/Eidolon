from __future__ import annotations
"""v2638 read-only Mind projection for restart-safe developer queue state."""
from typing import Any, Mapping
CONTRACT_VERSION='v2638.0'
def build_project_queue_restart_mind(recovery:Mapping[str,Any],review:Mapping[str,Any]|None=None)->dict[str,Any]:
 review=review if isinstance(review,Mapping) else {}
 reasons=[str(x)[:120] for x in recovery.get('failure_reasons') or []][:8]
 return {'ok':bool(recovery.get('ok')),'contract_version':CONTRACT_VERSION,'state':'recovered' if recovery.get('ok') else 'review_required','generation':int(recovery.get('generation') or 0),'project_count':int(review.get('project_count') or 0),'failure_reasons':reasons,'operator_review_required':bool(recovery.get('operator_review_required')),'content_minimized':True,'project_content_stored':False,'queue_mutation_permitted':False,'automatic_project_start_permitted':False,'authority_granted':False}
__all__=['CONTRACT_VERSION','build_project_queue_restart_mind']
