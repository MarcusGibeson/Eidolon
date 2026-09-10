import tempfile
from conscious_agent.live_internal_voice_runtime_v2530 import project_live_internal_voice
from conscious_agent.internal_voice_provider_audit_v2531 import build_internal_voice_provider_receipt

def main():
 ep={'ok':True,'episode_digest':'3'*64,'meaningful_changes':['belief_conflicts'],'steps':[{'operation':'RECONSIDER_BELIEF','outcome_type':'BELIEF_REVISION_CANDIDATE','reason_code':'conflict'}],'candidate_outcomes':['BELIEF_REVISION_CANDIDATE']};c=[]
 def ck(n,v):c.append((n,bool(v)))
 with tempfile.TemporaryDirectory() as td:
  off=project_live_internal_voice(ep,runtime_root=td,event_id='off');ck('default_off',not off['provider_contacted']);on=project_live_internal_voice(ep,runtime_root=td,event_id='on',provider_generate=lambda p:"I’m rechecking the conflict before I treat the earlier belief as settled.",provider_enabled=True,provider_allowed=True);rc=build_internal_voice_provider_receipt(on,episode_digest=ep['episode_digest']);ck('optional_provider',on['provider_candidate_used']);ck('receipt_minimized',not rc['voice_text_stored']);ck('fallback_exists',on['fallback_preserved']);ck('no_literal',not on['voice_events'][0]['claims_literal_thought_transcript']);ck('no_external_action',not rc['tool_executed'] and not rc['message_sent']);ck('no_authority',not on['authority_broadened'] and not rc['authority_broadened'])
 p=sum(v for _,v in c);print(f'v2532.9 live internal voice provider integration checkpoint: {p}/{len(c)}');[print('PASS' if v else 'FAIL',n) for n,v in c];raise SystemExit(0 if p==len(c) else 1)
if __name__=='__main__':main()
