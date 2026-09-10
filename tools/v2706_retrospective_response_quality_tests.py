from tempfile import TemporaryDirectory
from conscious_agent.response_quality_retrospective_v2706 import build_retrospective_response_quality
from conscious_agent.response_quality_history_v2702 import append_response_quality,append_retrospective_response_quality,load_response_quality_history
from conscious_agent.response_quality_trend_v2703 import build_response_quality_trend

def run():
 c=[]
 def ck(n,v):c.append((n,bool(v)))
 prior={'present':True,'grounding':{'operation_ref_digest':'a'*64,'assertiveness':'grounded'}}
 fb={'explicit_correction':True,'explicit_retraction':False,'adverse_calibration_evidence':True,'disposition':'grounded_claim_corrected'}
 r=build_retrospective_response_quality(prior,fb,evidence_operation_id='next-op');ck('bound_prior',r['target_operation_ref_digest']=='a'*64 and r['state']=='quality_concern')
 with TemporaryDirectory() as td:
  append_response_quality({'state':'unknown','evidence_strength':'none','quality_digest':'q','eligible_for_positive_learning':False,'eligible_for_negative_learning':False},{'outcome_digest':'o'},operation_id='ignored-different-op',runtime_root=td)
  # Inject original prior row using operation whose sha is not our synthetic ref; then append retrospective and verify preserved separately.
  append_retrospective_response_quality(r,runtime_root=td);rows=load_response_quality_history(td)['rows'];ck('revision_appended',rows[-1]['row_type']=='retrospective_revision' and rows[-1]['eligible_for_negative_learning'])
  t=build_response_quality_trend(rows,window=3);ck('trend_content_free',not t['raw_conversation_text_stored'])
 ck('no_text',not r['raw_prior_response_stored'] and not r['raw_correction_text_stored']);ck('no_policy',not r['automatic_policy_change'] and not r['authority_granted'])
 n=build_retrospective_response_quality({},fb,evidence_operation_id='x');ck('missing_prior_no_evidence',not n['evidence_recorded'])
 return {'ok':all(v for _,v in c),'checks':c,'passed':sum(v for _,v in c),'total':len(c)}
if __name__=='__main__':
 r=run();print(r);raise SystemExit(0 if r['ok'] else 1)
