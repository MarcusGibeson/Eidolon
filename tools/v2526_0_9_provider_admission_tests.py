from conscious_agent.internal_voice_verbalization_contract_v2525 import prepare_internal_voice_verbalization_request
from conscious_agent.internal_voice_provider_admission_v2526 import admit_internal_voice_provider_request

def main():
 ep={'ok':True,'episode_digest':'a'*64,'meaningful_changes':['uncertainty'],'steps':[]};r=prepare_internal_voice_verbalization_request(ep,enabled=True);c=[]
 def ck(n,v):c.append((n,bool(v)))
 a=admit_internal_voice_provider_request(r);ck('default_denied',not a['admitted']);b=admit_internal_voice_provider_request(r,runtime_enabled=True,provider_allowed=True);ck('exact_admit',b['admitted']);ck('limited',not b['general_provider_authority_granted'] and not b['tool_execution_authorized']);ck('bound',b['request_digest']==r['request_digest']);ck('digest',len(b['admission_digest'])==64)
 p=sum(v for _,v in c);print(f'v2526 provider admission: {p}/{len(c)}');[print('PASS' if v else 'FAIL',n) for n,v in c];raise SystemExit(0 if p==len(c) else 1)
if __name__=='__main__':main()
