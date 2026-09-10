from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from conscious_agent.bounded_evidence_compaction import *
from conscious_agent.bounded_evidence_compaction_checkpoint import build_bounded_evidence_compaction_checkpoint
from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
checks=[]
def require(value):checks.append(bool(value));assert value
def h(v):return hashlib.sha256(v.encode()).hexdigest()
snapshot=h('snapshot');context=h('context');rows=[];previous=''
for i,(domain,kind,outcome,uncertainty,approval,rollback) in enumerate([('conversation','observation','retained','none','not_required','not_applicable'),('reasoning','decision','revised','bounded','approved','available'),('campaign','transition','suspended','unresolved','deferred','verified'),('result','result','completed','none','approved','verified'),('learning','learning','retained','conflicted','review_required','unavailable')]):
 row=create_evidence_record(evidence_id=f'evidence-{i}',sequence=i,previous_evidence_digest=previous,snapshot_digest=snapshot,context_digest=context,artifact_digest=h(f'a{i}'),receipt_digest=h(f'r{i}'),domain=domain,evidence_kind=kind,outcome=outcome,uncertainty_code=uncertainty,approval_state=approval,rollback_state=rollback);rows.append(row);previous=row['evidence_digest']
report=compact_evidence(rows,snapshot_digest=snapshot,context_digest=context);require(report['status']=='compacted');require(report['compaction']['record_count']==5);require(report['compaction']['schema']==list(SCHEMA));require(report['content_free'] is True);require(report['execution_invoked'] is False)
expanded=expand_compaction(report,expected_snapshot_digest=snapshot,expected_context_digest=context);require(expanded['status']=='expanded');require(expanded['records']==rows)
equivalence=verify_compaction_equivalence(rows,report,snapshot_digest=snapshot,context_digest=context);require(equivalence['equivalent'] is True)
for key in ('historical_truth_preserved','approval_truth_preserved','rollback_truth_preserved','uncertainty_truth_preserved','authority_separation_preserved'):require(equivalence[key] is True)
summary=public_compaction_summary(report,equivalence);require(summary['record_count']==5);require(summary['content_free'] is True);require('rows' not in summary)
def resigned(row):
 copy=dict(row);copy.pop('evidence_digest',None);copy['evidence_digest']=hashlib.sha256(json.dumps(copy,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest();return copy
mutations=[]
x=[dict(r) for r in rows];x[1]['evidence_id']=x[0]['evidence_id'];x[1]=resigned(x[1]);mutations.append(x)
x=[dict(r) for r in rows];x[2]['previous_evidence_digest']=h('bad');x[2]=resigned(x[2]);mutations.append(x)
x=[dict(r) for r in rows];x[1]['snapshot_digest']=h('stale');x[1]=resigned(x[1]);mutations.append(x)
x=[dict(r) for r in rows];x[1]['context_digest']=h('stale');x[1]=resigned(x[1]);mutations.append(x)
x=[dict(r) for r in rows];x[1]['prompt']='secret';x[1]=resigned(x[1]);mutations.append(x)
x=[dict(r) for r in rows];x[1]['authority_state']='granted';x[1]=resigned(x[1]);mutations.append(x)
x=[dict(r) for r in rows];x[1]['outcome']='failed';mutations.append(x)
for case in mutations:
 blocked=compact_evidence(case,snapshot_digest=snapshot,context_digest=context);require(blocked['status']=='blocked');require(blocked['error_count']>0);require(blocked['authority_granted'] is False)
tampered=dict(report);tampered['compaction']=dict(report['compaction']);tampered['compaction']['record_count']=99
blocked=expand_compaction(tampered,expected_snapshot_digest=snapshot,expected_context_digest=context);require(blocked['status']=='blocked');require('compaction_tamper' in blocked['errors'])
checkpoint=build_bounded_evidence_compaction_checkpoint(source_root=ROOT);require(checkpoint['ok'] is True);require(checkpoint['passed']==checkpoint['total']);require(checkpoint['read_only'] is True);require(checkpoint['authority_granted'] is False)
registry=inspect_checkpoint_registry(source_root=ROOT);require(any(r['checkpoint_id']=='bounded-evidence-compaction-checkpoint' for r in registry['checkpoints']))
proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'bounded-evidence-compaction-checkpoint'],cwd=ROOT,text=True,capture_output=True,check=False);require(proc.returncode==0);require(json.loads(proc.stdout)['ok'] is True)
status,payload=dispatch_api('GET','/api/cognition/bounded-evidence-compaction-checkpoint');require(status==200);require(payload['data']['ok'] is True)
status,_=dispatch_api('POST','/api/cognition/bounded-evidence-compaction-checkpoint');require(status in {404,405})
html=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(encoding='utf-8');require('bounded-evidence-compaction-checkpoint-panel' in html);require('/api/cognition/bounded-evidence-compaction-checkpoint' in html)
release=(ROOT/'tools'/'release_verify.py').read_text(encoding='utf-8');require(release.count('v1192.2-bounded-evidence-compaction-foundations')==1)
metadata=(ROOT/'conscious_agent'/'release_metadata.py').read_text(encoding='utf-8');require('WORKING_SOURCE_VERSION = "1192.2"' in metadata);require('v1192.3-v1192.5' in metadata)
for name in ('README.md','README_NEXT_STEPS.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md','README_RELEASE_HISTORY.md'):
 text=(ROOT/name).read_text(encoding='utf-8');require('v1192.0-v1192.2' in text);require('v1192.3-v1192.5' in text)
print(json.dumps({'suite':'v1192.0-v1192.2-bounded-evidence-compaction','ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True))
