from __future__ import annotations
"""v2507.7-v2507.8 bridges existing receipts into content-free self observations."""
from typing import Any,Mapping
from developmental_self_model_v2507 import DevelopmentalSelfModelStore
CONTRACT_VERSION='v2507.8'

def observe_from_outcome_receipt(event_id:str,*,runtime_root,receipt:Mapping[str,Any],trait_code:str,domain:str,polarity:str='support')->dict[str,Any]:
 if not isinstance(receipt,Mapping):raise ValueError('receipt required')
 evidence=str(receipt.get('evidence_digest') or receipt.get('validation_digest') or receipt.get('receipt_digest') or '').lower();source=str(receipt.get('evidence_owner') or receipt.get('source_kind') or 'development_outcome').lower()
 if source not in {'benchmark_receipt','capability_receipt','development_outcome','cognitive_receipt','operator_verified','memory_consolidation_review'}:source='development_outcome'
 result=DevelopmentalSelfModelStore(runtime_root).observe(event_id,trait_code=trait_code,domain=domain,polarity=polarity,evidence_digest=evidence,source_kind=source,observation_code=str(receipt.get('outcome_code') or receipt.get('status') or trait_code))
 return {**result,'contract_version':CONTRACT_VERSION,'raw_receipt_persisted':False,'trait_applied':False,'identity_rewritten':False,'authority_broadened':False}

__all__=['CONTRACT_VERSION','observe_from_outcome_receipt']
