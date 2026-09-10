from pathlib import Path
import json,tempfile,hashlib
from conscious_agent.active_inquiry_records import ActiveInquiryStore
from conscious_agent.inquiry_activation_arbitration import InquiryActivationArbitrator
from conscious_agent.active_inquiry_continuity_checkpoint import build_active_inquiry_continuity_checkpoint

def req(v):
 if not v: raise AssertionError()
def sig(root):
 d=hashlib.sha256()
 for p in sorted(x for x in root.rglob('*') if x.is_file()):d.update(p.relative_to(root).as_posix().encode());d.update(p.read_bytes())
 return d.hexdigest()
with tempfile.TemporaryDirectory() as td:
 root=Path(td);(root/'curiosity_inquiry_promotions.json').write_text(json.dumps({'schema_version':'1','contract_version':'v1111.6','promotions':[{'inquiry_candidate_id':'c1','semantic_key':'s1','decision_id':'d1','question_id':'q1','project_digest':'p1','state':'candidate'}],'processed_events':[],'revision':1,'updated_at':'','controls':{'max_candidates':256,'max_active':48},'state_separation':{},'authority_boundary':{}}))
 store=ActiveInquiryStore(root,clock=lambda:'2026-07-27T12:00:00.000Z');iid=store.register('e1',inquiry_candidate_id='c1',expires_at='2026-08-01T00:00:00Z',reconsider_after='2026-07-28T00:00:00Z')['result']['active_inquiry_id'];InquiryActivationArbitrator(root,clock=lambda:'2026-07-27T12:01:00.000Z').decide('a1',active_inquiry_id=iid,relevance=.9,answerability=.8,novelty=.8,importance=.9)
 before=sig(root);c=build_active_inquiry_continuity_checkpoint(root,source_root=Path(td)/'source');after=sig(root)
 req(c['ok']);req(c['contract_version']=='v1113.2');req(len(c['checks'])==12);req(before==after);req(not c['runtime_mutated']);req(c['summary']['active_count']==1);req(not c['external_browsing_performed']);req(not c['provider_contacted']);req(not c['authorization_granted']);req(not c['raw_messages_exposed'])
print('10/10')

# CLI/API/dashboard exposure remains read-only.
import os,subprocess,sys
from conscious_agent.api_server import dispatch_api
status,payload=dispatch_api('GET','/api/cognition/active-inquiry-checkpoint');req(status==200 and (payload.get('data') or {}).get('contract_version')=='v1113.2')
status2,_=dispatch_api('POST','/api/cognition/active-inquiry-checkpoint',body={});req(status2!=200)
run=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'eidolon.py'),'active-inquiry-checkpoint','--json'],capture_output=True,text=True,env=dict(os.environ),timeout=60);req(run.returncode==0 and json.loads(run.stdout)['contract_version']=='v1113.2')
dash=(Path(__file__).resolve().parents[1]/'conscious_agent/dashboard_first_use.py').read_text();req('active-inquiry-checkpoint-panel' in dash and '/api/cognition/active-inquiry-checkpoint' in dash)
print('14/14 integration')
