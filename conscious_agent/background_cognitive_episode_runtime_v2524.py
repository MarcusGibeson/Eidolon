from __future__ import annotations
"""v2524 bounded background cognitive episodes with internal-voice projections."""
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping
from background_cognitive_runtime_v2505 import BackgroundCognitiveRuntime
from bounded_cognitive_episode_v2522 import build_bounded_cognitive_episode
from internal_voice_cadence_v2523 import InternalVoiceCadence
from json_storage import load_json_file, write_json_atomic
from mental_activity_timeline_v2511 import MentalActivityTimeline
from metadata_mutation_coordination import metadata_mutation_lock
from state_grounded_internal_voice_v2523 import project_episode_internal_voice
from unified_cognitive_state_frame import build_unified_cognitive_state_frame

CONTRACT_VERSION='v2524.5';SCHEMA_VERSION='1'
def _default():return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'revision':0,'last_frame':{},'recent_episodes':[],'controls':{'max_episodes':128},'authority_boundary':{'can_contact_provider':False,'can_send_message':False,'can_execute_action':False,'can_apply_candidate':False,'hidden_reasoning_exposed':False}}
class BackgroundCognitiveEpisodeRuntime:
 def __init__(self,runtime_root:str|Path):
  self.root=Path(runtime_root).expanduser().resolve();self.path=self.root/'background_cognitive_episode_v2524.json';self.background=BackgroundCognitiveRuntime(self.root);self.cadence=InternalVoiceCadence(self.root);self.timeline=MentalActivityTimeline(self.root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get('schema_version')!=SCHEMA_VERSION:s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def run(self,event_id:str,*,trigger_type:str='background_cadence',trigger_ref:str='',subject_ref:str='',new_experience:bool=False,self_model_evidence:bool=False,foreground_busy:bool=False,quiet_hours:bool=False,operator_paused:bool=False,sleeping:bool=False,resource_pressure:str='normal'):
  eid=' '.join(str(event_id or '').split())[:160]
  if not eid:raise ValueError('event_id required')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   state=self._load();existing=next((x for x in state['recent_episodes'] if x.get('event_id')==eid),None)
   if existing:return {'ok':True,'status':'episode_replayed','episode':deepcopy(existing),'idempotent':True,**self._denied()}
   frame=build_unified_cognitive_state_frame(self.root,trigger_type=trigger_type,trigger_ref=trigger_ref)
   previous=state.get('last_frame') if isinstance(state.get('last_frame'),Mapping) and state.get('last_frame',{}).get('frame_digest') else None
   episode=build_bounded_cognitive_episode(frame,previous_frame=previous,new_experience=new_experience,self_model_evidence=self_model_evidence)
   result=self.background.run_structural_tick(eid,trigger_type=trigger_type,trigger_ref=trigger_ref,subject_ref=subject_ref,new_experience=new_experience,self_model_evidence=self_model_evidence,foreground_busy=foreground_busy,quiet_hours=quiet_hours,operator_paused=operator_paused,sleeping=sleeping,resource_pressure=resource_pressure)
   voices=[]
   if result.get('status')=='background_structural_cognition_completed' and str(result.get('selected_operation'))==str(episode.get('initial_operation')):
    for idx,voice in enumerate(project_episode_internal_voice(episode),start=1):
     admission=self.cadence.admit(f'{eid}-voice-{idx}',voice_text=voice['voice_text'],source_digest=episode['episode_digest'])
     if admission.get('emit'):
      voices.append(voice)
      self.timeline.append(f'{eid}-timeline-voice-{idx}',event_kind='voice',transition='projection',source_digest=voice['voice_digest'],subject_ref=subject_ref,outcome_code=voice.get('voice_kind',''))
   row={'event_id':eid,'episode_digest':episode['episode_digest'],'frame_digest':frame['frame_digest'],'initial_operation':episode['initial_operation'],'step_count':episode['step_count'],'candidate_outcomes':episode['candidate_outcomes'],'background_status':str(result.get('status') or ''),'voice_count':len(voices),'voice_digests':[v['voice_digest'] for v in voices],'provider_contacted':False,'message_sent':False,'tool_executed':False,'source_mutated':False,'candidate_applied':False,'hidden_reasoning_exposed':False}
   state['last_frame']={'ok':True,'frame_digest':frame['frame_digest'],'projection':deepcopy(frame.get('projection') or {})}
   state['recent_episodes']=(state['recent_episodes']+[row])[-int(state['controls']['max_episodes']):];state['revision']+=1;write_json_atomic(self.path,state,expected_type=dict,sort_keys=True)
   return {'ok':True,'status':'background_cognitive_episode_completed' if result.get('status')=='background_structural_cognition_completed' else str(result.get('status') or 'background_episode_not_run'),'episode':deepcopy(row),'voice_events':deepcopy(voices),'background_result':result,'idempotent':False,**self._denied()}
 def _denied(self):return {'provider_contacted':False,'message_sent':False,'external_action_executed':False,'tool_executed':False,'source_mutated':False,'candidate_applied':False,'authority_broadened':False,'hidden_reasoning_exposed':False}
 def inspection_summary(self):
  s=self._load();return {'ok':True,'contract_version':CONTRACT_VERSION,'revision':s['revision'],'episode_count':len(s['recent_episodes']),'recent_episodes':deepcopy(s['recent_episodes'][-16:]),'authority_boundary':deepcopy(s['authority_boundary']),**self._denied()}
__all__=['CONTRACT_VERSION','BackgroundCognitiveEpisodeRuntime']
