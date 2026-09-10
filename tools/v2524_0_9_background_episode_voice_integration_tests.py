from __future__ import annotations
import tempfile
from pathlib import Path
from conscious_agent.background_cognitive_episode_runtime_v2524 import BackgroundCognitiveEpisodeRuntime
from conscious_agent.mental_activity_timeline_v2511 import MentalActivityTimeline

def main():
 checks=[]
 def ck(n,v):checks.append((n,bool(v)))
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);r=BackgroundCognitiveEpisodeRuntime(root);r.background.configure('cfg',enabled=True,minimum_interval_seconds=5,max_cycles_per_hour=8)
  out=r.run('e1',new_experience=True)
  ck('run_ok',out['ok']);ck('completed',out['status']=='background_cognitive_episode_completed');ck('episode',out['episode']['step_count']>=1);ck('voices',out['episode']['voice_count']>=1)
  ck('safe',not out['provider_contacted'] and not out['tool_executed'] and not out['candidate_applied']);ck('timeline_voice',MentalActivityTimeline(root).recent(kind='voice')['event_count']>=1)
  replay=r.run('e1',new_experience=True);ck('replay',replay['idempotent'])
  # A second immediate tick is governed by retained minimum-interval policy.
  second=r.run('e2',new_experience=True);ck('suppression_respected',second['status']!='background_cognitive_episode_completed')
  ins=r.inspection_summary();ck('inspection',ins['episode_count']>=1 and not ins['provider_contacted'])
 passed=sum(v for _,v in checks);print(f'v2524.0-9 background episode/voice integration: {passed}/{len(checks)}')
 for n,v in checks:print(('PASS' if v else 'FAIL'),n)
 raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__':main()
