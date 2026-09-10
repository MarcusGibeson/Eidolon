from __future__ import annotations
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from conscious_agent.evidence_compaction_reliability import *
from conscious_agent.evidence_compaction_reliability import _digest
from conscious_agent.evidence_compaction_reliability_checkpoint import build_evidence_compaction_reliability_checkpoint
from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
checks=[]
def require(x):checks.append(bool(x))
def h(x):return hashlib.sha256(x.encode()).hexdigest()
comp,term,snap,ctx=map(h,('comp','term','snap','ctx'));rows=[];prev=''
for i,(event,action) in enumerate((('interruption','preserve'),('restart','review_required'),('stale_compaction','rebuild_required'),('privacy','reject'),('outage','defer'))):
 r=create_reliability_record(record_id=f'reliability-record-{i}',event_type=event,action=action,compaction_digest=comp,terminal_evidence_digest=term,snapshot_digest=snap,context_digest=ctx,review_digest=h(f'review-{i}'),sequence=i,previous_record_digest=prev);rows.append(r);prev=r['record_digest']
good=assess_compaction_reliability(records=rows,current_compaction_digest=comp,current_terminal_evidence_digest=term,current_snapshot_digest=snap,current_context_digest=ctx)
for value in (good['ok'],good['status']=='reliability_verified',good['record_count']==5,good['original_evidence_preserved'],not good['automatic_recovery'],not good['replacement_performed'],not good['deletion_performed'],not good['execution_invoked'],not good['provider_contacted'],not good['model_contacted'],not good['thread_started'],not good['process_started'],not good['runtime_modified'],not good['authority_granted']):require(value)
summary=public_reliability_summary(good);require(summary['content_free']);require(summary['record_count']==5)
def blocked(rs=rows,**kw):
 x=assess_compaction_reliability(records=rs,current_compaction_digest=kw.get('comp',comp),current_terminal_evidence_digest=kw.get('term',term),current_snapshot_digest=kw.get('snap',snap),current_context_digest=kw.get('ctx',ctx));require(not x['ok']);require(x['status']=='blocked');require(not x['execution_invoked']);require(not x['authority_granted']);return x
blocked(comp=h('x'));blocked(term=h('x'));blocked(snap=h('x'));blocked(ctx=h('x'))
for field,value in [('event_type','bad'),('action','bad'),('content_free',False),('automatic_recovery',True),('replacement_performed',True),('deletion_performed',True),('execution_invoked',True),('authority_granted',True)]:
 bad=[dict(x) for x in rows];bad[2][field]=value;bad[2].pop('record_digest');bad[2]['record_digest']=_digest(bad[2]);blocked(bad)
bad=[dict(x) for x in rows];bad[2]['record_digest']='0'*64;blocked(bad)
bad=[dict(x) for x in rows];bad[2]['prompt']='private';blocked(bad)
bad=[dict(x) for x in rows];bad[2]['sequence']=1;bad[2].pop('record_digest');bad[2]['record_digest']=_digest(bad[2]);blocked(bad)
bad=[dict(x) for x in rows];bad[2]['previous_record_digest']=h('wrong');bad[2].pop('record_digest');bad[2]['record_digest']=_digest(bad[2]);blocked(bad)
bad=[dict(x) for x in rows];bad[2]['record_id']=bad[1]['record_id'];bad[2].pop('record_digest');bad[2]['record_digest']=_digest(bad[2]);blocked(bad)
bad=[dict(x) for x in rows];bad[2]['review_digest']=bad[1]['review_digest'];bad[2].pop('record_digest');bad[2]['record_digest']=_digest(bad[2]);x=blocked(bad);require(x['replay_detected'])
cp=build_evidence_compaction_reliability_checkpoint(source_root=ROOT);require(cp['ok']);require(cp['source_unchanged'])
reg=inspect_checkpoint_registry(source_root=ROOT);require(any(r['checkpoint_id']=='evidence-compaction-reliability-checkpoint' for r in reg['checkpoints']))
proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'evidence-compaction-reliability-checkpoint'],cwd=ROOT,text=True,capture_output=True);require(proc.returncode==0);require(json.loads(proc.stdout)['ok'])
status,payload=dispatch_api('GET','/api/cognition/evidence-compaction-reliability-checkpoint');require(status==200);require(payload['data']['ok'])
status,_=dispatch_api('POST','/api/cognition/evidence-compaction-reliability-checkpoint');require(status in {404,405})
html=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(encoding='utf-8');require('evidence-compaction-reliability-checkpoint-panel' in html);require('/api/cognition/evidence-compaction-reliability-checkpoint' in html)
release=(ROOT/'tools'/'release_verify.py').read_text(encoding='utf-8');require(release.count('v1192.8-evidence-compaction-reliability')==1)
meta=(ROOT/'conscious_agent'/'release_metadata.py').read_text(encoding='utf-8');require('WORKING_SOURCE_VERSION = "1192.8"' in meta);require('v1192.9' in meta)
for name in ('README.md','README_NEXT_STEPS.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md','README_RELEASE_HISTORY.md'):
 t=(ROOT/name).read_text(encoding='utf-8');require('v1192.6-v1192.8' in t);require('v1192.9' in t)
print(json.dumps({'suite':'v1192.6-v1192.8-evidence-compaction-reliability','ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True))
