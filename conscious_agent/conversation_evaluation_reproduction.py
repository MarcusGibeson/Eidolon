from __future__ import annotations
"""v1087.3 privacy-safe reproduction packets for explicit operator evaluations."""
from typing import Any, Mapping
import hashlib, json, platform
from conversation_daily_evaluation import load_daily_evaluation
from release_metadata import RUNTIME_VERSION, RUNTIME_MILESTONE

def _digest(value: Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()

def build_reproduction_packet(evaluation_id: str)->dict[str,Any]:
    summary=load_daily_evaluation(evaluation_id)
    observations=list(summary.get('observations') or ())
    packet={
      'type':'desktop_alpha_evaluation_reproduction_packet','schema_version':'1',
      'runtime_version':RUNTIME_VERSION,'runtime_milestone':RUNTIME_MILESTONE,
      'evaluation_id':summary['evaluation_id'],'evaluation_state':summary['state'],
      'evaluation_revision':summary['revision'],'session_reference_digest':_digest(summary.get('session_id','')),
      'readiness_contract_digest':summary.get('readiness_contract_digest',''),
      'readiness_areas_digest':summary.get('readiness_areas_digest',''),
      'observation_count':summary.get('observation_count',0),
      'observation_evidence_digest':summary.get('observation_evidence_digest',''),
      'outcome_code':((summary.get('outcome') or {}).get('outcome') or (summary.get('outcome') or {}).get('outcome_code','')),
      'issue_domains':sorted({str(x.get('issue_domain')) for x in observations if x.get('issue_domain') not in {None,'none'}}),
      'severities':sorted({str(x.get('severity')) for x in observations if x.get('severity') not in {None,'none'}}),
      'signals':sorted({str(s) for x in observations for s in list(x.get('signals') or ())}),
      'reproducible_observation_count':sum(1 for x in observations if x.get('reproducible')),
      'environment':{'python_implementation':platform.python_implementation(),'platform_family':platform.system().lower() or 'unknown'},
      'transcript_included':False,'prompt_included':False,'private_notes_included':False,'provider_payload_included':False,
      'credentials_included':False,'vectors_included':False,'hidden_reasoning_included':False,
      'provider_invoked':False,'writes_state':False,'content_free':True,'redacted':True,
    }
    packet['packet_digest']=_digest(packet)
    return packet

def reproduction_packet_contains_private_fields(value: Mapping[str,Any]|None)->bool:
    forbidden={'note','notes','content','text','message','transcript','prompt','provider_payload','credentials','vectors','embedding','hidden_reasoning','chain_of_thought'}
    stack=[value]
    while stack:
      cur=stack.pop()
      if isinstance(cur,Mapping):
        if forbidden & {str(k) for k in cur}: return True
        stack.extend(cur.values())
      elif isinstance(cur,(list,tuple)): stack.extend(cur)
    return False
