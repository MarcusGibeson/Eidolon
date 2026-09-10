from tempfile import TemporaryDirectory
from conscious_agent.response_outcome_followup_signal_v2707 import build_response_outcome_followup_signal
from conscious_agent.response_quality_positive_retrospective_v2708 import build_positive_retrospective_quality
from conscious_agent.response_quality_history_v2702 import append_positive_retrospective_quality,load_response_quality_history

def run():
 c=[]
 def ck(n,v):c.append((n,bool(v)))
 for text in ['That fixed it','that worked','Yes, that is exactly what I needed','That answers my question','problem solved']:
  s=build_response_outcome_followup_signal(text);ck('positive_'+str(len(c)),s['positive_resolution'] and s['kind']=='confirmed_resolution')
 ck('thanks_not_enough',not build_response_outcome_followup_signal('thanks')['explicit'])
 neg=build_response_outcome_followup_signal('that worked',{'candidate':{'candidate_type':'correction'}});ck('correction_precedence',neg['negative_followup'] and not neg['positive_resolution'])
 prior={'grounding':{'operation_ref_digest':'b'*64}};pos=build_positive_retrospective_quality(prior,build_response_outcome_followup_signal('that worked'),evidence_operation_id='next');ck('prior_bound',pos['evidence_recorded'] and pos['state']=='supported_success')
 with TemporaryDirectory() as td:
  append_positive_retrospective_quality(pos,runtime_root=td);rows=load_response_quality_history(td)['rows'];ck('positive_revision',rows[-1]['eligible_for_positive_learning'] and rows[-1]['state']=='supported_success')
 ck('no_text',not pos['raw_message_stored'] and not pos['raw_prior_response_stored']);ck('no_authority',not pos['authority_granted'])
 return {'ok':all(v for _,v in c),'checks':c,'passed':sum(v for _,v in c),'total':len(c)}
if __name__=='__main__':
 r=run();print(r);raise SystemExit(0 if r['ok'] else 1)
