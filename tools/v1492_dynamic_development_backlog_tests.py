from __future__ import annotations
import os,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=Path(tempfile.mkdtemp(prefix='eidolon-v1492-'));os.environ['EIDOLON_DATA_DIR']=str(R);os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.dynamic_development_backlog import DynamicDevelopmentBacklog
from conscious_agent.development_authority import issue_operator_authorization
p=f=0
def ck(n,c,d=''):
 global p,f
 if c:p+=1;print('PASS',n)
 else:f+=1;print('FAIL',n,d)
try:
 comp={'comparison_digest':'c'*64,'ordered_comparison':[{'candidate_id':'a','quality_score':.9,'quality_class':'strong','uncertainty':'low'},{'candidate_id':'b','quality_score':.7,'quality_class':'credible','uncertainty':'medium'}]}
 store=DynamicDevelopmentBacklog(R);r=store.ingest_comparison('e1',comp);r2=store.ingest_comparison('e1',comp)
 ck('comparison becomes durable backlog items',r['created']==2 and store.snapshot()['revision']==1,r)
 ck('backlog ingestion is exactly-once by event id',r2['idempotent'] and store.snapshot()['revision']==1,r2)
 restarted=DynamicDevelopmentBacklog(R);s=restarted.progress_summary()
 ck('backlog survives restart',s['item_count']==2 and s['highest_review_candidate_id']=='a',s)
 blocked=restarted.transition('e2','a','operator_selected')
 ck('operator selection cannot be inferred automatically',blocked['status']=='transition_blocked',blocked)
 phrase='Select candidate a.';selection_receipt=issue_operator_authorization(stage='candidate_selection',subject_id='a',subject_digest='1'*64,explicit_operator_text=phrase,expected_operator_text=phrase)
 selected=restarted.transition('e3','a','operator_selected',evidence_digest='1'*64,operator_authorization_receipt=selection_receipt)
 ck('exact operator selection is recorded',selected['state']=='operator_selected',selected)
 blocked_install=restarted.transition('e4','a','installed',evidence_digest='2'*64)
 ck('installation transition cannot skip lifecycle or infer authority',blocked_install['status']=='transition_blocked' and blocked_install['reason']=='illegal_state_transition',blocked_install)
 planned=restarted.transition('e5','a','planned',evidence_digest='2'*64)
 workspace_phrase='Prepare candidate a workspace.';workspace_receipt=issue_operator_authorization(stage='workspace_preparation',subject_id='a',subject_digest='2'*64,explicit_operator_text=workspace_phrase,expected_operator_text=workspace_phrase)
 workspace=restarted.transition('e6','a','workspace_authorized',evidence_digest='3'*64,authority_digest='2'*64,operator_authorization_receipt=workspace_receipt)
 implemented=restarted.transition('e7','a','implemented',evidence_digest='4'*64)
 verified=restarted.transition('e8','a','verified',evidence_digest='5'*64)
 review=restarted.transition('e9','a','review_ready',evidence_digest='6'*64)
 ck('non-authority progress follows legal evidence-bound lifecycle',all(row['status']=='backlog_transitioned' for row in (planned,workspace,implemented,verified,review)),review)
 install_phrase='Install candidate a.';install_receipt=issue_operator_authorization(stage='installation',subject_id='a',subject_digest='7'*64,explicit_operator_text=install_phrase,expected_operator_text=install_phrase)
 installed=restarted.transition('e10','a','installed',evidence_digest='7'*64,operator_authorization_receipt=install_receipt)
 ck('sealed operator installation admission records terminal state',installed['state']=='installed',installed)
 summary=restarted.progress_summary()
 ck('progress summary remains content free and non-mutating',summary['content_free'] and not summary['selection_made_automatically'] and not summary['source_modified'] and not summary['provider_contacted'],summary)
 print({'ok':f==0,'passed':p,'failed':f,'suite':'v1492-dynamic-development-backlog','content_free':True})
finally:shutil.rmtree(R,ignore_errors=True)
if f:raise SystemExit(1)
