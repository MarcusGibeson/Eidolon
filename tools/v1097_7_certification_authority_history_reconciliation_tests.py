from __future__ import annotations
import json,shutil,tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
for item in (ROOT/'conscious_agent',ROOT/'tools'):sys.path.insert(0,str(item))
from v1097_bundle_c_test_support import prepare_certified_fixture
from release_candidate_identity import digest_payload,read_json
from release_certification_history import create_certification_history_reconciliation_preview,certification_history_status

def c(n,o):return {'name':n,'ok':bool(o)}
def clone(src:Path,base:Path,name:str)->Path:
 d=base/name;shutil.copytree(src,d);return d
def save_digest(path:Path,field:str):
 d=read_json(path);d.pop(field,None);d[field]=digest_payload(d);path.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def main():
 rows=[]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-7-') as td:
  base=Path(td);f=prepare_certified_fixture(base/'seed');rr=Path(f['handoff_runtime']);cert=rr/'release_certification'
  before={str(p.relative_to(cert)):p.read_bytes() for p in cert.rglob('*') if p.is_file()}
  good=create_certification_history_reconciliation_preview(runtime_root=rr);status=certification_history_status(runtime_root=rr)
  after={k:(cert/k).read_bytes() for k in before}
  rows += [c('coherent-history',good.get('ok') and good.get('history_integrity')=='coherent'),c('history-bound',bool(good.get('history_sha256')) and bool(good.get('record_inventory_sha256'))),c('read-only-authority-records',before==after),c('status-no-preview-generation-change',status.get('generation')==good.get('generation'))]
  # duplicate generation and fork
  r=clone(rr,base,'dup');states=list((r/'release_certification/states').glob('*.json'));d=read_json(states[0]);d['state_id']='duplicate-state';d.pop('state_sha256',None);d['state_sha256']=digest_payload(d);(states[0].parent/'duplicate-state.json').write_text(json.dumps(d));out=create_certification_history_reconciliation_preview(runtime_root=r);rows.append(c('duplicate-generation-detected',any(x['kind']=='duplicate_state_generation' for x in out.get('findings',[]))))
  r=clone(rr,base,'gap');p=list((r/'release_certification/states').glob('*.json'))[0];d=read_json(p);d['generation']=3;d.pop('state_sha256',None);d['state_sha256']=digest_payload(d);p.write_text(json.dumps(d));out=create_certification_history_reconciliation_preview(runtime_root=r);rows.append(c('missing-generation-detected',any(x['kind']=='missing_state_generation' for x in out.get('findings',[]))))
  r=clone(rr,base,'fork');p=list((r/'release_certification/states').glob('*.json'))[0];d=read_json(p);prev=d['state_sha256'];
  for i in (2,3):
   q=dict(d);q['state_id']=f'fork-{i}';q['generation']=i;q['previous_state_sha256']=prev;q.pop('state_sha256',None);q['state_sha256']=digest_payload(q);(p.parent/f'fork-{i}.json').write_text(json.dumps(q))
  out=create_certification_history_reconciliation_preview(runtime_root=r);rows.append(c('fork-detected',any(x['kind']=='authority_history_fork' for x in out.get('findings',[]))))
  r=clone(rr,base,'orphan');receipt={'schema':'eidolon-certification-decision-receipt-v1','certification_transaction_id':'orphan'};receipt['receipt_sha256']=digest_payload(receipt);(r/'release_certification/receipts/orphan.json').write_text(json.dumps(receipt));out=create_certification_history_reconciliation_preview(runtime_root=r);rows.append(c('orphan-receipt-detected',any(x['kind']=='orphan_certification_receipt' for x in out.get('findings',[]))))
  r=clone(rr,base,'broken');p=list((r/'release_certification/evidence').glob('*.json'))[0];d=read_json(p);d['producer_version']='tampered';p.write_text(json.dumps(d));out=create_certification_history_reconciliation_preview(runtime_root=r);rows.append(c('broken-digest-detected',any(x['kind']=='evidence_digest_link_broken' for x in out.get('findings',[]))))
  for label,field,kind in [('candidate','candidate_id','cross_candidate_history_link'),('project','target_project_id','cross_project_history_link'),('promotion','promotion_receipt_sha256','cross_promotion_history_link')]:
   r=clone(rr,base,label);p=list((r/'release_certification/evidence').glob('*.json'))[0];d=read_json(p);d[field]='wrong';d.pop('record_sha256',None);d['record_sha256']=digest_payload(d);p.write_text(json.dumps(d));out=create_certification_history_reconciliation_preview(runtime_root=r);rows.append(c(f'cross-{label}-detected',any(x['kind']==kind for x in out.get('findings',[]))))
  public=json.dumps(good);rows += [c('path-privacy','/tmp/' not in public and str(rr) not in public),c('history-preserved',all((cert/k).read_bytes()==v for k,v in before.items()))]
 report={'suite':'v1097.7-certification-authority-history-reconciliation','passed':sum(x['ok'] for x in rows),'failed':sum(not x['ok'] for x in rows),'checks':rows};report['ok']=report['failed']==0;print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
