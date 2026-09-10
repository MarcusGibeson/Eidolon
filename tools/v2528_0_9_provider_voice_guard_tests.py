import tempfile
from conscious_agent.internal_voice_provider_guard_v2528 import admit_provider_voice_candidate

def main():
 c=[]
 def ck(n,v):c.append((n,bool(v)))
 base={'status':'verbalization_candidate_created','candidate':{'voice_text':"I’m checking whether the current evidence still supports the earlier conclusion.",'candidate_digest':'c'*64,'source_request_digest':'d'*64}}
 with tempfile.TemporaryDirectory() as td:
  a=admit_provider_voice_candidate(base,runtime_root=td,event_id='1');ck('admit',a['emit']);b=admit_provider_voice_candidate(base,runtime_root=td,event_id='2');ck('repeat_suppressed',not b['emit']);bad={'status':'verbalization_candidate_created','candidate':{'voice_text':'Here is my hidden reasoning and chain-of-thought.','candidate_digest':'e'*64}};z=admit_provider_voice_candidate(bad,runtime_root=td,event_id='3');ck('unsafe_rejected',not z['emit']);ck('no_literal_claim',not a['claims_literal_thought_transcript']);ck('no_authority',not a['authority_broadened'])
 p=sum(v for _,v in c);print(f'v2528 provider voice guard: {p}/{len(c)}');[print('PASS' if v else 'FAIL',n) for n,v in c];raise SystemExit(0 if p==len(c) else 1)
if __name__=='__main__':main()
