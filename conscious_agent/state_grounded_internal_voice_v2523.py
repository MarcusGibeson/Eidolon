from __future__ import annotations
"""v2523 richer internal-voice projection grounded in cognitive episodes/deltas."""
import hashlib, json
from typing import Any, Mapping
CONTRACT_VERSION='v2523.5'

def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _delta(delta:Mapping[str,Any],name:str)->float:
 try:return float(((delta.get('deltas') or {}).get(name) or {}).get('delta') or 0)
 except (TypeError,ValueError):return 0.0

def _episode_lines(episode:Mapping[str,Any],delta:Mapping[str,Any]|None=None)->list[tuple[str,str]]:
 d=delta or {}; lines=[]; changes=set(episode.get('meaningful_changes') or d.get('meaningful_changes') or [])
 if 'uncertainty' in changes:
  lines.append(('observation', "My uncertainty has shifted, so I’m checking whether the earlier picture still holds." if _delta(d,'uncertainty')>=0 else "The uncertainty has eased, so I can narrow what still needs attention."))
 if 'belief_conflicts' in changes or 'contested_beliefs' in changes:
  lines.append(('observation', "There is more conflict in what I currently retain, so I shouldn’t treat the earlier conclusion as settled."))
 if 'pressure' in changes or 'fragmentation' in changes:
  lines.append(('observation', "The cognitive load has changed enough that I’m adjusting how much attention this deserves right now."))
 if 'due_subjects' in changes:
  lines.append(('observation', "An unfinished subject has become relevant again, so I’m bringing it back into focus."))
 steps=list(episode.get('steps') or [])
 for step in steps[:3]:
  op=str(step.get('operation') or '').upper(); reason=str(step.get('reason_code') or '')
  text={
   'RECONSIDER_BELIEF':"I’m rechecking a belief rather than carrying it forward unchanged.",
   'RESOLVE_CONFLICT':"I’m trying to reconcile the conflicting state before I rely on either side.",
   'REVIEW_GOAL':"I’m checking whether the current goal still deserves the same priority.",
   'REPLAN':"The current route may not fit the evidence anymore, so I’m reconsidering the plan.",
   'PLAN':"I’m organizing the next step before I treat the goal as actionable.",
   'INTEGRATE_EXPERIENCE':"I’m connecting this experience to what I already retain instead of leaving it isolated.",
   'REFLECT':"I’m holding this concern in focus long enough to see whether anything meaningful changes.",
   'CONTINUE_THOUGHT':"I’m returning to an unfinished line of thought instead of starting over.",
   'REVIEW_SELF_MODEL':"I’m comparing this behavior with the evidence I retain about my own tendencies.",
   'REST':"Nothing useful needs more cognition from me right now.",
  }.get(op)
  if text: lines.append(('process',text))
 if episode.get('candidate_outcomes'):
  lines.append(('conclusion',"I found a possible state update, but it remains only a candidate until the proper boundary accepts it."))
 elif steps and steps[-1].get('outcome_type')=='NO_DURABLE_CHANGE':
  lines.append(('conclusion',"I don’t have a durable change to make from this pass."))
 out=[]; seen=set()
 for kind,text in lines:
  if text not in seen:seen.add(text);out.append((kind,text))
 return out[:5]

def project_episode_internal_voice(episode:Mapping[str,Any],*,delta:Mapping[str,Any]|None=None)->list[dict[str,Any]]:
 if not isinstance(episode,Mapping) or not episode.get('ok') or not episode.get('episode_digest'):raise ValueError('valid cognitive episode required')
 rows=[]
 for idx,(kind,text) in enumerate(_episode_lines(episode,delta),start=1):
  row={'event':'internal_voice','contract_version':CONTRACT_VERSION,'voice_kind':kind,'voice_text':text,'episode_digest':str(episode['episode_digest'])[:64],'sequence':idx,'representation_kind':'state_grounded_internal_voice_projection','provider_contacted':False,'hidden_reasoning_exposed':False,'claims_literal_thought_transcript':False,'raw_cognitive_content_stored':False,'content_minimized':True}
  row['voice_digest']=_digest(row);rows.append(row)
 return rows

def project_activity_internal_voice_beta(activity:Mapping[str,Any])->dict[str,Any]|None:
 if str(activity.get('event') or '')!='activity':return None
 stage=str(activity.get('stage') or '').lower(); digest=str(activity.get('activity_digest') or '')
 variants={
  'accepted':("I’m orienting to the request before I decide what matters most.","I’m getting the request into context before I respond."),
  'context':("I’m checking the conversation state and what I already retain that may matter here.","I’m pulling the current context together before committing to an answer."),
  'governed_action':("This may involve action, so I’m checking the authority boundary before anything moves.",),
  'action_proposed':("I’ve recognized an action candidate, but recognition is not permission to execute it.",),
  'action_result':("I have a governed result receipt now, so I can reason from what actually happened.",),
  'response_complete':("I have enough processed state to finish this response.","The relevant work is resolved enough for me to answer now."),
  'saved':("I’ve preserved the completed turn so the next interaction doesn’t have to begin from zero.",),
  'error':("Something failed, so I’m stopping at the boundary instead of inventing a clean ending.",),
 }
 choices=variants.get(stage)
 if not choices:return None
 pick=int(digest[:8],16)%len(choices) if digest and len(digest)>=8 else 0;text=choices[pick]
 row={'event':'internal_voice','contract_version':CONTRACT_VERSION,'voice_kind':'process','voice_text':text,'grounded_stage':stage,'source_activity_digest':digest[:64],'representation_kind':'state_grounded_internal_voice_projection','provider_contacted':False,'hidden_reasoning_exposed':False,'claims_literal_thought_transcript':False,'raw_prompt_stored':False,'raw_provider_output_stored':False,'content_minimized':True}
 row['voice_digest']=_digest(row);return row
__all__=['CONTRACT_VERSION','project_episode_internal_voice','project_activity_internal_voice_beta']
