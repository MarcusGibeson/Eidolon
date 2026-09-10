from __future__ import annotations
import tempfile
from pathlib import Path
from conscious_agent.bounded_cognitive_episode_v2522 import build_bounded_cognitive_episode
from conscious_agent.cognitive_state_delta_v2522 import compare_cognitive_frames
from conscious_agent.state_grounded_internal_voice_v2523 import project_episode_internal_voice, project_activity_internal_voice_beta
from conscious_agent.internal_voice_verbalization_contract_v2525 import prepare_internal_voice_verbalization_request
from conscious_agent.background_cognitive_episode_runtime_v2524 import BackgroundCognitiveEpisodeRuntime
from conscious_agent.mental_activity_timeline_v2511 import MentalActivityTimeline

def _frame(digest='a'*64, uncertainty=.1, conflicts=0):
 return {'ok':True,'frame_digest':digest,'projection':{'homeostasis':{'pressure':.1,'uncertainty':uncertainty,'fragmentation':0,'recovery_margin':1},'demands':{'candidate_count':1},'beliefs':{'active_conflict_count':conflicts,'contested_count':conflicts},'planning':{'active_count':1},'continuity':{'due_subject_count':0},'initiative':{}}}
def main():
 checks=[]
 def ck(n,v):checks.append((n,bool(v)))
 a=_frame();b=_frame('b'*64,.5,1);delta=compare_cognitive_frames(a,b);ep=build_bounded_cognitive_episode(b,previous_frame=a);voices=project_episode_internal_voice(ep,delta=delta);req=prepare_internal_voice_verbalization_request(ep)
 ck('delta_grounded','uncertainty' in delta['meaningful_changes']);ck('episode_bounded',1<=ep['step_count']<=3);ck('voice_grounded',len(voices)>=2 and all(v['episode_digest']==ep['episode_digest'] for v in voices));ck('voice_not_literal',all(not v['claims_literal_thought_transcript'] for v in voices));ck('verbalization_disabled',not req['enabled'] and not req['provider_contact_authorized']);ck('verbalization_minimized',not req['raw_prompt_included'] and not req['raw_reasoning_included'])
 act=project_activity_internal_voice_beta({'event':'activity','stage':'context','activity_digest':'c'*64});ck('activity_beta',bool(act and act['voice_text']))
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);rt=BackgroundCognitiveEpisodeRuntime(root);rt.background.configure('cfg',enabled=True,minimum_interval_seconds=5,max_cycles_per_hour=8);out=rt.run('episode',new_experience=True)
  ck('background_episode',out['status']=='background_cognitive_episode_completed');ck('background_voice',len(out['voice_events'])>=1);ck('timeline_projection',MentalActivityTimeline(root).recent(kind='voice')['event_count']>=1);ck('no_external_authority',not out['provider_contacted'] and not out['tool_executed'] and not out['candidate_applied'])
 passed=sum(v for _,v in checks);print(f'v2525.9 richer internal cognition/internal voice checkpoint: {passed}/{len(checks)}')
 for n,v in checks:print(('PASS' if v else 'FAIL'),n)
 raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__':main()
