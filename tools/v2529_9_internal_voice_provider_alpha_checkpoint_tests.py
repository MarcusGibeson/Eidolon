import tempfile
from conscious_agent.internal_voice_verbalization_contract_v2525 import prepare_internal_voice_verbalization_request
from conscious_agent.internal_voice_provider_admission_v2526 import admit_internal_voice_provider_request
from conscious_agent.internal_voice_provider_runtime_v2527 import run_internal_voice_verbalization
from conscious_agent.internal_voice_provider_guard_v2528 import admit_provider_voice_candidate

def main():
 c=[]
 def ck(n,v):c.append((n,bool(v)))
 ep={'ok':True,'episode_digest':'f'*64,'meaningful_changes':['belief_conflicts'],'steps':[{'operation':'RECONSIDER_BELIEF','outcome_type':'BELIEF_REVISION_CANDIDATE','reason_code':'conflict'}]};r=prepare_internal_voice_verbalization_request(ep,enabled=True);deny=admit_internal_voice_provider_request(r);ck('default_off',not deny['admitted']);a=admit_internal_voice_provider_request(r,runtime_enabled=True,provider_allowed=True);x=run_internal_voice_verbalization(r,a,provider_generate=lambda p:"I’m rechecking the conflicting evidence before I carry the earlier belief forward.")
 with tempfile.TemporaryDirectory() as td:g=admit_provider_voice_candidate(x,runtime_root=td,event_id='checkpoint');ck('provider_path',x['provider_contacted']);ck('voice_emit',g['emit']);ck('candidate_only',x['candidate_only']);ck('no_raw',not x['raw_provider_output_stored']);ck('no_tool',not x['tool_executed']);ck('no_message',not x['message_sent']);ck('not_literal',not g['claims_literal_thought_transcript']);ck('no_broad_authority',not a['general_provider_authority_granted'] and not g['authority_broadened'])
 p=sum(v for _,v in c);print(f'v2529.9 internal voice provider alpha checkpoint: {p}/{len(c)}');[print('PASS' if v else 'FAIL',n) for n,v in c];raise SystemExit(0 if p==len(c) else 1)
if __name__=='__main__':main()
