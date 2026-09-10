from __future__ import annotations
"""Read-only v1192.2 Bounded Evidence Compaction Foundations checkpoint."""
import hashlib, os
from pathlib import Path
from typing import Any
from bounded_evidence_compaction import create_evidence_record, compact_evidence, expand_compaction, verify_compaction_equivalence, public_compaction_summary
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
CONTRACT_VERSION="v1192.2"
_CHECKPOINT_ID="bounded-evidence-compaction:v1192.2"
_LIMITATIONS=("Compaction is caller-supplied, bounded, and content-free.","No retained runtime evidence is deleted or rewritten.","No approval, rollback, execution, provider/model operation, or authority is invoked.","Operator review and durable compaction acceptance are deferred to v1192.3-v1192.5.","Desktop Codex and native-provider review remain deferred until v1200.")
def _h(value:str)->str:return hashlib.sha256(value.encode("utf-8")).hexdigest()
def _tree(root:Path):
 h=hashlib.sha256();n=0
 for base,dirs,files in os.walk(root):
  dirs[:]=[d for d in dirs if d not in {'data','sandbox','.git','.venv','venv','__pycache__','.pytest_cache','dist','build','reports'}]
  for name in sorted(files):
   p=Path(base)/name
   if p.suffix.lower() in {'.pyc','.pyo'}:continue
   try:b=p.read_bytes();rel=p.relative_to(root).as_posix()
   except OSError:continue
   n+=1;h.update(rel.encode());h.update(b'\0');h.update(hashlib.sha256(b).digest())
 return h.hexdigest(),n
def _records(snapshot,context):
 specs=[('evidence-0001','conversation','observation','retained','none','not_required','not_applicable'),('evidence-0002','reasoning','decision','revised','bounded','approved','available'),('evidence-0003','campaign','transition','suspended','unresolved','deferred','verified'),('evidence-0004','result','result','completed','none','approved','verified'),('evidence-0005','learning','learning','retained','conflicted','review_required','unavailable')]
 rows=[];previous=''
 for sequence,(eid,domain,kind,outcome,uncertainty,approval,rollback) in enumerate(specs):
  row=create_evidence_record(evidence_id=eid,sequence=sequence,previous_evidence_digest=previous,snapshot_digest=snapshot,context_digest=context,artifact_digest=_h(eid+':artifact'),receipt_digest=_h(eid+':receipt'),domain=domain,evidence_kind=kind,outcome=outcome,uncertainty_code=uncertainty,approval_state=approval,rollback_state=rollback)
  rows.append(row);previous=row['evidence_digest']
 return rows
def build_bounded_evidence_compaction_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 source=Path(source_root or Path(__file__).resolve().parents[1]).resolve();del runtime_root
 before,count=_tree(source);checks=[];req=lambda value:checks.append(bool(value));snapshot=_h('v1191.9:snapshot');context=_h('v1192.2:context');records=_records(snapshot,context)
 compacted=compact_evidence(records,snapshot_digest=snapshot,context_digest=context);expanded=expand_compaction(compacted,expected_snapshot_digest=snapshot,expected_context_digest=context);equivalence=verify_compaction_equivalence(records,compacted,snapshot_digest=snapshot,context_digest=context);summary=public_compaction_summary(compacted,equivalence)
 for value in (compacted.get('status')=='compacted',expanded.get('status')=='expanded',expanded.get('records')==records,equivalence.get('equivalent') is True,summary.get('record_count')==5,summary.get('historical_truth_preserved') is True,summary.get('approval_truth_preserved') is True,summary.get('rollback_truth_preserved') is True,summary.get('uncertainty_truth_preserved') is True,summary.get('authority_separation_preserved') is True):req(value)
 blocked={}
 def case(name,mutate,*,snap=snapshot,ctx=context):
  rows=[dict(r) for r in records];mutate(rows);blocked[name]=compact_evidence(rows,snapshot_digest=snap,context_digest=ctx)
 def resign(row):
  row.pop('evidence_digest',None);import json;row['evidence_digest']=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
 case('duplicate-id',lambda r:(r[1].__setitem__('evidence_id',r[0]['evidence_id']),resign(r[1])))
 case('broken-lineage',lambda r:(r[2].__setitem__('previous_evidence_digest',_h('wrong')),resign(r[2])))
 case('stale-snapshot',lambda r:(r[1].__setitem__('snapshot_digest',_h('stale')),resign(r[1])))
 case('private-field',lambda r:(r[1].__setitem__('prompt','secret'),resign(r[1])))
 case('authority',lambda r:(r[1].__setitem__('authority_state','granted'),resign(r[1])))
 case('tamper',lambda r:r[1].__setitem__('outcome','failed'))
 for report in blocked.values():req(report.get('status')=='blocked');req(report.get('error_count',0)>0);req(report.get('execution_invoked') is False);req(report.get('authority_granted') is False)
 stale=dict(compacted);stale['compaction']=dict(compacted['compaction']);stale['compaction']['snapshot_digest']=_h('stale')
 stale_expansion=expand_compaction(stale,expected_snapshot_digest=snapshot,expected_context_digest=context);req(stale_expansion.get('status')=='blocked');req('compaction_tamper' in stale_expansion.get('errors',[]))
 registry=inspect_checkpoint_registry(source_root=source);req(any(r.get('checkpoint_id')=='bounded-evidence-compaction-checkpoint' for r in registry.get('checkpoints',[])))
 privacy=package_privacy_summary_for_root(source);req(privacy.get('ok') is True)
 after,after_count=_tree(source);req(before==after);req(count==after_count)
 return {'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract_version':CONTRACT_VERSION,'checkpoint_id':_CHECKPOINT_ID,'read_only':True,'post_available':False,'content_free':True,'summary':summary,'blocked_cases':{k:v.get('errors',[]) for k,v in blocked.items()},'stale_compaction_errors':stale_expansion.get('errors',[]),'limitations':list(_LIMITATIONS),'source_unchanged':before==after,'source_file_count':count,'provider_contacted':False,'model_contacted':False,'thread_started':False,'process_started':False,'execution_invoked':False,'approval_consumed':False,'rollback_invoked':False,'authority_granted':False}
