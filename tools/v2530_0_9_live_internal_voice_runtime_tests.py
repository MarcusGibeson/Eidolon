import tempfile
from conscious_agent.live_internal_voice_runtime_v2530 import project_live_internal_voice

def main():
 ep={'ok':True,'episode_digest':'1'*64,'meaningful_changes':['uncertainty'],'steps':[{'operation':'REFLECT','outcome_type':'NO_DURABLE_CHANGE','reason_code':'concern'}],'candidate_outcomes':[]};c=[]
 def ck(n,v):c.append((n,bool(v)))
 with tempfile.TemporaryDirectory() as td:
  a=project_live_internal_voice(ep,runtime_root=td,event_id='a');ck('default_fallback',a['status']=='deterministic_voice_fallback' and not a['provider_contacted']);seen=[];b=project_live_internal_voice(ep,runtime_root=td,event_id='b',provider_generate=lambda p:(seen.append(p) or "I’m checking whether this uncertainty changes what deserves attention."),provider_enabled=True,provider_allowed=True);ck('provider_used',b['provider_candidate_used'] and b['provider_contacted']);ck('bounded_call',len(seen)==1);ck('not_literal',not b['voice_events'][0]['claims_literal_thought_transcript']);ck('fallback_preserved',b['fallback_preserved']);ck('no_authority',not b['authority_broadened'])
 p=sum(v for _,v in c);print(f'v2530 live internal voice runtime: {p}/{len(c)}');[print('PASS' if v else 'FAIL',n) for n,v in c];raise SystemExit(0 if p==len(c) else 1)
if __name__=='__main__':main()
