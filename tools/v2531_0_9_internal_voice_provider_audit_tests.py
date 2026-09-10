from conscious_agent.internal_voice_provider_audit_v2531 import build_internal_voice_provider_receipt

def main():
 r=build_internal_voice_provider_receipt({'status':'provider_voice_projected','provider_contacted':True,'provider_candidate_used':True,'voice_events':[{'voice_text':'secret?'}],'fallback_preserved':True},episode_digest='2'*64);c=[]
 def ck(n,v):c.append((n,bool(v)))
 ck('digest',len(r['receipt_digest'])==64);ck('content_minimized',not r['voice_text_stored'] and not r['raw_provider_output_stored']);ck('provider_fact',r['provider_contacted']);ck('no_action',not r['tool_executed'] and not r['message_sent']);ck('no_authority',not r['authority_broadened'])
 p=sum(v for _,v in c);print(f'v2531 provider audit: {p}/{len(c)}');[print('PASS' if v else 'FAIL',n) for n,v in c];raise SystemExit(0 if p==len(c) else 1)
if __name__=='__main__':main()
