from conscious_agent.internal_voice_verbalization_contract_v2525 import prepare_internal_voice_verbalization_request
from conscious_agent.internal_voice_provider_admission_v2526 import admit_internal_voice_provider_request
from conscious_agent.internal_voice_provider_runtime_v2527 import run_internal_voice_verbalization

def main():
 ep={'ok':True,'episode_digest':'b'*64,'meaningful_changes':['uncertainty'],'steps':[{'operation':'REFLECT','outcome_type':'NO_DURABLE_CHANGE','reason_code':'concern'}]};r=prepare_internal_voice_verbalization_request(ep,enabled=True);c=[]
 def ck(n,v):c.append((n,bool(v)))
 d=run_internal_voice_verbalization(r,admit_internal_voice_provider_request(r),provider_generate=lambda p:'no');ck('denied_no_call',not d['provider_contacted']);seen=[];a=admit_internal_voice_provider_request(r,runtime_enabled=True,provider_allowed=True);x=run_internal_voice_verbalization(r,a,provider_generate=lambda p:(seen.append(p) or "I’m reconsidering the current uncertainty before I settle on a conclusion."));ck('called',x['provider_contacted'] and len(seen)==1);ck('candidate_only',x['candidate_only'] and not x['provider_result_admitted']);ck('no_raw',not x['raw_provider_output_stored'] and not x['raw_prompt_stored']);ck('bounded_input',len(seen[0])<=1800);ck('no_action',not x['tool_executed'] and not x['message_sent'])
 p=sum(v for _,v in c);print(f'v2527 provider runtime: {p}/{len(c)}');[print('PASS' if v else 'FAIL',n) for n,v in c];raise SystemExit(0 if p==len(c) else 1)
if __name__=='__main__':main()
