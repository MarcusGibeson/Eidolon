from __future__ import annotations
import os,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=tempfile.mkdtemp(prefix='eidolon-v1498-');os.environ['EIDOLON_DATA_DIR']=R;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True;sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.continuous_development_campaign import new_campaign,apply_campaign_event,campaign_public_projection
from conscious_agent.development_authority import issue_operator_authorization
p=f=0
def ck(n,c,d=''):
 global p,f
 if c:p+=1;print('PASS',n)
 else:f+=1;print('FAIL',n,d)
def ev(i,a,**kw):return {'event_id':i,'action':a,'current_source_digest':'a'*64,**kw}
try:
 s=new_campaign(campaign_id='camp',candidate_id='cand',baseline_source_digest='a'*64)
 r=apply_campaign_event(s,ev('e1','record_comparison',evidence_digest='1'*64));s=r['state'];ck('campaign records evidence in order',r['accepted'] and s['stage']=='compared',r)
 blocked=apply_campaign_event(s,ev('e2','operator_select',evidence_digest='2'*64));ck('campaign cannot infer operator selection',not blocked['accepted'] and blocked['reason']=='operator_authority_required',blocked)
 selection_phrase='Select campaign candidate.';selection=issue_operator_authorization(stage='candidate_selection',subject_id='cand',subject_digest='2'*64,explicit_operator_text=selection_phrase,expected_operator_text=selection_phrase)
 r=apply_campaign_event(s,ev('e2','operator_select',evidence_digest='2'*64,operator_authorization_receipt=selection));s=r['state'];ck('exact operator selection advances campaign',s['stage']=='operator_selected' and s['operator_selected'],r)
 r=apply_campaign_event(s,ev('e3','record_plan',evidence_digest='3'*64));s=r['state']
 workspace_phrase='Authorize campaign workspace.';workspace=issue_operator_authorization(stage='workspace_preparation',subject_id='cand',subject_digest='3'*64,explicit_operator_text=workspace_phrase,expected_operator_text=workspace_phrase)
 r=apply_campaign_event(s,ev('e4','authorize_workspace',evidence_digest='4'*64,authority_digest='3'*64,operator_authorization_receipt=workspace));s=r['state'];r=apply_campaign_event(s,ev('e5','record_implementation',evidence_digest='5'*64));s=r['state'];r=apply_campaign_event(s,ev('e6','record_verification',evidence_digest='6'*64));s=r['state'];r=apply_campaign_event(s,ev('e7','record_review',evidence_digest='7'*64));s=r['state']
 ck('campaign can coordinate through review-ready without install',s['stage']=='review_ready' and not s['installation_authorized'],s)
 dup=apply_campaign_event(s,ev('e7','record_review',evidence_digest='7'*64));ck('replayed event is exactly-once',dup['duplicate'] and dup['accepted'] and dup['state']['state_digest']==s['state_digest'],dup)
 collision=apply_campaign_event(s,ev('e7','stop',reason='different'));ck('event id collision fails closed',collision['duplicate'] and not collision['accepted'],collision)
 concurrent=new_campaign(campaign_id='c2',candidate_id='cand',baseline_source_digest='a'*64);changed=apply_campaign_event(concurrent,{'event_id':'x','action':'record_comparison','current_source_digest':'b'*64,'evidence_digest':'1'*64});ck('authoritative source change stops campaign before reuse',changed['state']['stage']=='stopped' and changed['reason']=='authoritative_source_changed',changed)
 out=campaign_public_projection(s);ck('public campaign projection grants no source provider install promotion authority',not any(out[k] for k in ('provider_contacted','source_modified','installation_authorized','promotion_authorized')),out)
 print({'ok':f==0,'passed':p,'failed':f,'suite':'v1498-continuous-development-campaign','content_free':True})
finally:shutil.rmtree(R,ignore_errors=True)
if f:raise SystemExit(1)
