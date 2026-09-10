from __future__ import annotations
from conscious_agent.internal_voice_verbalization_contract_v2525 import prepare_internal_voice_verbalization_request,validate_verbalization_candidate

def main():
 checks=[]
 def ck(n,v):checks.append((n,bool(v)))
 ep={'ok':True,'episode_digest':'c'*64,'meaningful_changes':['uncertainty'],'steps':[{'operation':'RECONSIDER_BELIEF','outcome_type':'BELIEF_REVISION_CANDIDATE','reason_code':'belief_conflict_present'}],'candidate_outcomes':['BELIEF_REVISION_CANDIDATE']}
 r=prepare_internal_voice_verbalization_request(ep)
 ck('request',len(r['request_digest'])==64);ck('disabled',not r['enabled']);ck('no_provider_authority',not r['provider_contact_authorized'] and not r['execution_ready']);ck('minimized',not r['raw_prompt_included'] and not r['raw_reasoning_included']);ck('facts_bounded',len(r['facts'])<=8);ck('grounded',r['source_episode_digest']=='c'*64)
 c=validate_verbalization_candidate(r,"I’m checking whether this belief still fits the conflicting evidence.")
 ck('candidate',c['ok'] and c['candidate_only']);ck('not_admitted',not c['provider_result_admitted']);ck('not_literal',not c['claims_literal_thought_transcript']);ck('bounded',len(c['voice_text'])<=320)
 passed=sum(v for _,v in checks);print(f'v2525.0-9 internal voice verbalization contract: {passed}/{len(checks)}')
 for n,v in checks:print(('PASS' if v else 'FAIL'),n)
 raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__':main()
