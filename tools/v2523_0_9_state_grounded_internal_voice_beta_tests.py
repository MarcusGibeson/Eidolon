from __future__ import annotations
import tempfile
from pathlib import Path
from conscious_agent.internal_voice_cadence_v2523 import InternalVoiceCadence
from conscious_agent.state_grounded_internal_voice_v2523 import project_episode_internal_voice,project_activity_internal_voice_beta

def main():
 checks=[]
 def ck(n,v):checks.append((n,bool(v)))
 ep={'ok':True,'episode_digest':'a'*64,'meaningful_changes':['uncertainty','belief_conflicts'],'steps':[{'operation':'RECONSIDER_BELIEF','outcome_type':'BELIEF_REVISION_CANDIDATE','reason_code':'belief_conflict_present'}],'candidate_outcomes':['BELIEF_REVISION_CANDIDATE']}
 d={'deltas':{'uncertainty':{'delta':.2}},'meaningful_changes':['uncertainty','belief_conflicts']}
 rows=project_episode_internal_voice(ep,delta=d)
 ck('rows',len(rows)>=3);ck('grounded',all(x['episode_digest']=='a'*64 for x in rows));ck('not_literal',all(not x['claims_literal_thought_transcript'] for x in rows));ck('no_provider',all(not x['provider_contacted'] for x in rows));ck('kinds',{'observation','process','conclusion'}.issubset({x['voice_kind'] for x in rows}))
 act={'event':'activity','stage':'context','activity_digest':'b'*64}
 v=project_activity_internal_voice_beta(act);ck('activity_voice',bool(v and 'context' in v['grounded_stage']));ck('activity_safe',not v['raw_prompt_stored'] and not v['provider_contacted'])
 with tempfile.TemporaryDirectory() as td:
  c=InternalVoiceCadence(Path(td));r1=c.admit('e1',voice_text=rows[0]['voice_text'],source_digest='a'*64);r2=c.admit('e2',voice_text=rows[0]['voice_text'],source_digest='a'*64)
  ck('first_emit',r1['emit']);ck('repeat_suppressed',not r2['emit'] and r2['suppression_reason']=='repeated_voice');ck('summary',c.inspection_summary()['emitted_count']==1)
 passed=sum(v for _,v in checks);print(f'v2523.0-9 state-grounded internal voice beta: {passed}/{len(checks)}')
 for n,v in checks:print(('PASS' if v else 'FAIL'),n)
 raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__':main()
