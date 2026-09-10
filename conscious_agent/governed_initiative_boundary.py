from __future__ import annotations
"""Governed initiative/silence boundary for v1489 Bundle 13.

This module classifies initiative artifacts and surfacing eligibility. It never
sends a message, notification, command, or provider request by itself.
"""
from dataclasses import dataclass,asdict
from typing import Any,Mapping,Iterable
import hashlib,json,time

ARTIFACT_CLASSES=frozenset({'internal_thought','private_journal','suggestion','notification','spoken_message'})
SURFACEABLE_CLASSES=frozenset({'suggestion','notification','spoken_message'})

@dataclass(frozen=True)
class InitiativeBoundaryDecision:
    artifact_class:str
    salient:bool
    cooldown_clear:bool
    novel:bool
    operator_muted:bool
    surface_eligible:bool
    reason:str
    can_send:bool=False
    can_execute:bool=False
    authority_changed:bool=False
    content_free:bool=True
    def public_summary(self)->dict[str,Any]:
        row=asdict(self); row['decision_digest']=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':')).encode()).hexdigest(); return row

def classify_artifact(kind:str)->str:
    token=str(kind or '').strip().lower().replace(' ','_')
    return token if token in ARTIFACT_CLASSES else 'internal_thought'

def salience_score(*, novelty:float, relevance:float, confidence:float)->float:
    n=max(0.0,min(1.0,float(novelty))); r=max(0.0,min(1.0,float(relevance))); c=max(0.0,min(1.0,float(confidence)))
    return round(.4*n+.4*r+.2*c,4)

def decide_surface(*,artifact_class:str,novelty:float,relevance:float,confidence:float,last_surface_epoch:float|None=None,now_epoch:float|None=None,cooldown_seconds:int=3600,muted:bool=False,repetitive:bool=False)->InitiativeBoundaryDecision:
    kind=classify_artifact(artifact_class); score=salience_score(novelty=novelty,relevance=relevance,confidence=confidence); salient=score>=.65
    now=time.time() if now_epoch is None else float(now_epoch); clear=last_surface_epoch is None or now-float(last_surface_epoch)>=max(0,int(cooldown_seconds))
    novel=bool(not repetitive and novelty>=.35)
    if kind not in SURFACEABLE_CLASSES: eligible=False; reason='private_artifact_boundary'
    elif muted: eligible=False; reason='operator_muted'
    elif not salient: eligible=False; reason='below_salience_threshold'
    elif not novel: eligible=False; reason='repetitive_self_loop'
    elif not clear: eligible=False; reason='cooldown_active'
    else: eligible=True; reason='eligible_for_operator_surface_review'
    return InitiativeBoundaryDecision(kind,salient,clear,novel,bool(muted),eligible,reason)

def preserved_unfinished_thought(*,thought_id:str,state:str='unfinished')->dict[str,Any]:
    return {'thought_id_digest':hashlib.sha256(str(thought_id or '').encode()).hexdigest()[:24],'state':str(state or 'unfinished'),'resume_allowed':True,'surface_allowed':False,'message_sent':False,'content_free':True}

def operator_controls(*,muted:bool=False,dismissed:bool=False,invited:bool=False)->dict[str,Any]:
    return {'muted':bool(muted),'dismissed':bool(dismissed),'operator_invited_surface':bool(invited),'operator_can_inspect':True,'operator_can_dismiss':True,'operator_can_mute':True,'autonomous_send_authority':False,'content_free':True}

def emotional_authority_guard(*,emotional_state:str,requested_action:str)->dict[str,Any]:
    return {'emotional_state_class':str(emotional_state or 'neutral')[:40],'requested_action_class':str(requested_action or '')[:60],'command_authority_changed':False,'release_authority_changed':False,'model_authority_changed':False,'content_free':True}
