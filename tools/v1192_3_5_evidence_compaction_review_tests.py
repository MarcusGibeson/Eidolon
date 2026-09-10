from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from conscious_agent.bounded_evidence_compaction import create_evidence_record, compact_evidence, verify_compaction_equivalence
from conscious_agent.evidence_compaction_review import *
from conscious_agent.evidence_compaction_review_checkpoint import build_evidence_compaction_review_checkpoint
from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
checks=[]
def require(value): checks.append(bool(value)); assert value
def h(value): return hashlib.sha256(value.encode()).hexdigest()
snapshot=h('snapshot'); context=h('context'); rows=[]; previous=''
for i in range(4):
 row=create_evidence_record(evidence_id=f'evidence-review-{i}',sequence=i,previous_evidence_digest=previous,snapshot_digest=snapshot,context_digest=context,artifact_digest=h(f'a{i}'),receipt_digest=h(f'r{i}'),domain=('conversation','reasoning','campaign','learning')[i],evidence_kind=('observation','decision','transition','learning')[i],outcome=('retained','revised','suspended','retained')[i],uncertainty_code=('none','bounded','unresolved','conflicted')[i],approval_state=('not_required','approved','deferred','review_required')[i],rollback_state=('not_applicable','available','verified','unavailable')[i]); rows.append(row); previous=row['evidence_digest']
compacted=compact_evidence(rows,snapshot_digest=snapshot,context_digest=context); equiv=verify_compaction_equivalence(rows,compacted,snapshot_digest=snapshot,context_digest=context); require(equiv['equivalent'] is True)
eq_digest=h(equiv['original_digest']+equiv['expanded_digest'])
request=create_compaction_review_request(request_id='compaction-request-1192',compaction_digest=compacted['compaction_digest'],terminal_evidence_digest=previous,snapshot_digest=snapshot,context_digest=context,record_count=4,equivalence_digest=eq_digest)
require(request['content_free'] is True); require(request['replacement_requested'] is False); require(request['deletion_requested'] is False)
for decision,status in (('approve','review_approved'),('reject','review_rejected'),('defer','review_deferred')):
 review=create_compaction_review(request_digest=request['request_digest'],decision=decision,review_id=f'compaction-{decision}-1192',operator_review_digest=h(decision))
 result=review_compaction(request=request,review=review,current_snapshot_digest=snapshot,current_context_digest=context,current_compaction_digest=compacted['compaction_digest'],current_terminal_evidence_digest=previous,equivalence_verified=True)
 require(result['status']==status); require(result['original_evidence_preserved'] is True); require(result['replacement_performed'] is False); require(result['deletion_performed'] is False); require(result['execution_invoked'] is False); require(result['authority_granted'] is False)
 if decision=='approve': require(public_compaction_review_summary(result)['compaction_retention_presented'] is True)
def run(rq=request,rv=None,**kw):
 if rv is None: rv=create_compaction_review(request_digest=rq['request_digest'],decision='approve',review_id='blocked-review-1192',operator_review_digest=h('blocked'))
 return review_compaction(request=rq,review=rv,current_snapshot_digest=kw.get('snapshot',snapshot),current_context_digest=kw.get('context',context),current_compaction_digest=kw.get('compaction',compacted['compaction_digest']),current_terminal_evidence_digest=kw.get('terminal',previous),equivalence_verified=kw.get('equivalent',True))
for blocked in (run(snapshot=h('stale')),run(context=h('stale')),run(compaction=h('stale')),run(terminal=h('stale')),run(equivalent=False)):
 require(blocked['status']=='blocked'); require(blocked['replacement_performed'] is False); require(blocked['authority_granted'] is False)
for field in ('replacement_requested','deletion_requested','execution_requested','automatic_acceptance','authority_requested'):
 bad=dict(request); bad[field]=True; result=run(bad); require(result['status']=='blocked'); require('hidden_mutation_or_authority_claim' in result['errors'])
bad=dict(request); bad['prompt']='secret'; require(run(bad)['status']=='blocked')
bad=dict(request); bad['request_digest']='0'*64; require('tampered_request' in run(bad)['errors'])
bad=dict(request); bad['record_count']=65; bad.pop('request_digest'); bad['request_digest']=hashlib.sha256(json.dumps(bad,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest(); require('invalid_record_count' in run(bad)['errors'])
checkpoint=build_evidence_compaction_review_checkpoint(source_root=ROOT); require(checkpoint['ok'] is True); require(checkpoint['passed']==checkpoint['total']); require(checkpoint['original_evidence_preserved'] if 'original_evidence_preserved' in checkpoint else checkpoint['summary']['original_evidence_preserved'])
registry=inspect_checkpoint_registry(source_root=ROOT); require(any(row['checkpoint_id']=='evidence-compaction-review-checkpoint' for row in registry['checkpoints']))
proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'evidence-compaction-review-checkpoint'],cwd=ROOT,text=True,capture_output=True,check=False); require(proc.returncode==0); require(json.loads(proc.stdout)['ok'] is True)
status,payload=dispatch_api('GET','/api/cognition/evidence-compaction-review-checkpoint'); require(status==200); require(payload['data']['ok'] is True)
status,_=dispatch_api('POST','/api/cognition/evidence-compaction-review-checkpoint'); require(status in {404,405})
html=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(encoding='utf-8'); require('evidence-compaction-review-checkpoint-panel' in html); require('/api/cognition/evidence-compaction-review-checkpoint' in html)
release=(ROOT/'tools'/'release_verify.py').read_text(encoding='utf-8'); require(release.count('v1192.5-operator-evidence-compaction-review')==1)
metadata=(ROOT/'conscious_agent'/'release_metadata.py').read_text(encoding='utf-8'); require('WORKING_SOURCE_VERSION = "1192.5"' in metadata); require('v1192.6-v1192.8' in metadata)
for name in ('README.md','README_NEXT_STEPS.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md','README_RELEASE_HISTORY.md'):
 text=(ROOT/name).read_text(encoding='utf-8'); require('v1192.3-v1192.5' in text); require('v1192.6-v1192.8' in text)
print(json.dumps({'suite':'v1192.3-v1192.5-evidence-compaction-review','ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True))
