from __future__ import annotations
"""Bounded relationship/preference continuity rules for ordinary conversation.

The guard separates durable explicit preference evidence from temporary tone. It
never infers milestones from assistant prose or transient affect, and all durable
mutation remains explicit through the existing curation service.
"""
from dataclasses import dataclass, asdict
import hashlib,json,re
from typing import Any, Iterable, Mapping
from memory_provenance_integrity import classify_memory_provenance

SCHEMA_VERSION='1'
_NICK_REQ=re.compile(r"(?i)\b(?:call me|you can call me|please call me|my nickname is|i go by)\s+([A-Za-z][A-Za-z0-9' -]{0,40})")
_NICK_STOP=re.compile(r"(?i)\b(?:stop|don't|do not|please don't|please do not)\b.{0,28}\b(?:call(?:ing)? me|nickname|pet name)\b")
_STABLE_PREF=re.compile(r"(?i)\b(?:from now on|going forward|i prefer|please always|please never|remember that)\b")
_TEMP_TONE=re.compile(r"(?i)\b(?:right now|today|for this reply|this time|at the moment|for now)\b")
_AFFECTION=re.compile(r"(?i)\b(?:love|adore|miss|sweet|cute|affection|dear|darling|pet name|nickname)\b")
_MOOD=re.compile(r"(?i)\b(?:tired|happy|sad|rough|excited|relieved|frustrated|proud|worried|calm|good|bad)\b")

@dataclass(frozen=True)
class RelationshipPreferenceGuardProfile:
    stable_preference_cue: bool
    temporary_tone_cue: bool
    nickname_request: bool
    nickname_rejection: bool
    affection_user_led: bool
    mood_warmth_allowed: bool
    fabricated_emotional_knowledge_allowed: bool=False
    content_free: bool=True
    schema_version: str=SCHEMA_VERSION
    def public_summary(self)->dict[str,Any]:
        d=asdict(self); d['profile_digest']=hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:24]; return d
    def prompt_lines(self)->tuple[str,...]:
        out=[]
        if self.nickname_rejection:
            out.append('Stop the rejected nickname or pet name immediately; explicit rejection overrides every older cue.')
        elif self.nickname_request:
            out.append('Use the explicitly requested name naturally; do not invent a different nickname or claim it was saved unless durable curation confirms that.')
        if self.temporary_tone_cue:
            out.append('Treat this tone request as temporary unless the user explicitly marks it as a durable preference.')
        if self.affection_user_led:
            out.append('Personality may add bounded warmth, but explicit affection/name preferences always win and intimacy must not escalate.')
        if self.mood_warmth_allowed:
            out.append('Respond warmly to the mood stated in this message without claiming hidden emotional knowledge.')
        return tuple(out)

def build_relationship_preference_guard(message:str)->RelationshipPreferenceGuardProfile:
    t=' '.join(str(message or '').split())
    return RelationshipPreferenceGuardProfile(
        stable_preference_cue=bool(_STABLE_PREF.search(t) and not _TEMP_TONE.search(t)),
        temporary_tone_cue=bool(_TEMP_TONE.search(t)),
        nickname_request=bool(_NICK_REQ.search(t)),
        nickname_rejection=bool(_NICK_STOP.search(t)),
        affection_user_led=bool(_AFFECTION.search(t)),
        mood_warmth_allowed=bool(_MOOD.search(t)),
    )

def explicit_nickname_from_message(message:str)->str:
    m=_NICK_REQ.search(' '.join(str(message or '').split()))
    return (m.group(1).strip(' .,!?:;') if m else '')[:40]

def relationship_milestone_evidence_eligible(record:Mapping[str,Any])->bool:
    """Only attributable user interaction may establish a relationship milestone."""
    if not isinstance(record,Mapping): return False
    profile=classify_memory_provenance(record)
    if not profile.provenance_valid or profile.quarantined or profile.provenance_class!='user': return False
    typ=str(record.get('type') or '').lower()
    return typ in {'important_moment','relationship','conversation_user'} and bool(str(record.get('content') or '').strip())

def stable_preference_records(records:Iterable[Mapping[str,Any]])->list[Mapping[str,Any]]:
    out=[]
    for row in records:
        if not isinstance(row,Mapping): continue
        if str(row.get('type') or '').lower() not in {'preference','nickname'}: continue
        if row.get('relationship_eligible') is False or str(row.get('status') or '').lower() in {'retracted','deleted','rejected'}: continue
        out.append(row)
    return out
