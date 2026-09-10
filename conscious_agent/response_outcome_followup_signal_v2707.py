from __future__ import annotations
"""v2707 narrow explicit follow-up resolution signals.

The message is inspected transiently; raw text is never returned or persisted.
Correction/retraction evidence has precedence over positive confirmation.
"""
from typing import Any, Mapping
import hashlib,json,re
CONTRACT_VERSION='v2707.0'
_POSITIVE=(
    re.compile(r"\bthat (?:fixed|solved) it\b",re.I),
    re.compile(r"\bthat worked\b",re.I),
    re.compile(r"\b(?:yes,?\s*)?that(?:'s| is) exactly what i (?:meant|needed|wanted)\b",re.I),
    re.compile(r"\bthat answers (?:it|my question)\b",re.I),
    re.compile(r"\bproblem solved\b",re.I),
)
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_response_outcome_followup_signal(message:str, learning_projection:Mapping[str,Any]|None=None)->dict[str,Any]:
    learning=dict(learning_projection or {});candidate=learning.get('candidate') if isinstance(learning.get('candidate'),Mapping) else {}
    ctype=str(candidate.get('candidate_type') or 'none')
    if ctype in {'correction','retraction'}:
        kind=ctype;explicit=True;positive=False;negative=True
    else:
        explicit=any(p.search(str(message or '')) for p in _POSITIVE)
        kind='confirmed_resolution' if explicit else 'none';positive=explicit;negative=False
    out={'ok':True,'contract_version':CONTRACT_VERSION,'explicit':explicit,'kind':kind,'positive_resolution':positive,'negative_followup':negative,
         'raw_message_stored':False,'raw_response_stored':False,'automatic_learning_applied':False,'authority_granted':False};out['signal_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_response_outcome_followup_signal']
