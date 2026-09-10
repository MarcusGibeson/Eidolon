from __future__ import annotations
import json, os, tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1097_bundle_a_test_support import prepare_promoted_fixture,evidence_payload,write_evidence
from release_certification_evidence import select_certification_evidence,create_certification_readiness_preview,certification_readiness_status,certification_directory
from api_server import ApiError,handle_api_get,handle_api_post
from dashboard import render_release_certification

def c(name,ok):return {"name":name,"ok":bool(ok)}

def main():
 rows=[]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-1-') as td:
  base=Path(td);f=prepare_promoted_fixture(base);rt=f['handoff_runtime']
  initial=create_certification_readiness_preview(runtime_root=rt)
  rows.append(c('missing-evidence-remains-not-ready',initial.get('ok') and not initial.get('ready') and len(initial.get('missing_scopes',[]))==4))
  for scope in ('source_package_integrity','startup_daily_use','installation_recovery','promotion_behavior'):
   p=write_evidence(base/'evidence'/f'{scope}.json',evidence_payload(f,scope));r=select_certification_evidence(p,runtime_root=rt);rows.append(c(f'explicit-{scope}-accepted',r.get('ok') and r.get('sufficient') and r.get('artifact_sha256')))
  ready=create_certification_readiness_preview(runtime_root=rt);status=certification_readiness_status(runtime_root=rt)
  rows += [c('general-release-ready',ready.get('ok') and ready.get('ready') and ready.get('status')=='certification_ready'),c('readiness-stable',status.get('ok') and status.get('ready')),c('scope-separation',set(ready.get('not_applicable_scopes',[]))=={'native_windows_behavior','provider_ollama_behavior','model_specific_behavior'}),c('paths-suppressed',str(base) not in json.dumps(ready,sort_keys=True) and ready.get('content_free'))]
  native_bad=write_evidence(base/'evidence'/'native-bad.json',evidence_payload(f,'native_windows_behavior'))
  nb=select_certification_evidence(native_bad,runtime_root=rt);rows.append(c('posix-not-native-windows',not nb.get('ok') and any(x['kind']=='native_windows_environment_not_proven' for x in nb.get('contradictions',[]))))
  malformed=base/'evidence'/'malformed.json';malformed.write_text('{bad',encoding='utf-8');mr=select_certification_evidence(malformed,runtime_root=rt);rows.append(c('malformed-insufficient',not mr.get('ok') and mr.get('status')=='evidence_insufficient'))
  stale=evidence_payload(f,'source_package_integrity');stale['candidate_id']='wrong';sr=select_certification_evidence(write_evidence(base/'evidence'/'stale.json',stale),runtime_root=rt);rows.append(c('contradictory-binding-insufficient',not sr.get('ok') and any('candidate_id_mismatch' in x['kind'] for x in sr.get('contradictions',[]))))
  leak=evidence_payload(f,'source_package_integrity');leak['report_path']=str(base/'private'/'report.json');lr=select_certification_evidence(write_evidence(base/'evidence'/'leak.json',leak),runtime_root=rt);rows.append(c('path-leaking-insufficient',not lr.get('ok') and any(x['kind']=='evidence_payload_leaks_private_path' for x in lr.get('contradictions',[]))))
  selfassert=evidence_payload(f,'source_package_integrity',producer='operator-self-assertion');ar=select_certification_evidence(write_evidence(base/'evidence'/'self.json',selfassert),runtime_root=rt);rows.append(c('self-asserted-insufficient',not ar.get('ok') and any(x['kind']=='self_asserted_or_untrusted_evidence' for x in ar.get('contradictions',[]))))
  # Evidence is selected only through explicit calls; sibling files remain unknown.
  sibling=write_evidence(base/'evidence'/'newest-looking.json',evidence_payload(f,'provider_ollama_behavior',environment={'provider':'ollama','available':True}));index=json.loads((certification_directory(rt)/'evidence_index.json').read_text());rows.append(c('no-directory-scan-or-newest-inference',all('newest-looking' not in x for x in index.get('evidence_ids',[])) and sibling.is_file()))
  previous=os.environ.get('EIDOLON_DATA_DIR');os.environ['EIDOLON_DATA_DIR']=str(rt)
  code,payload=handle_api_get('/api/release-certification/readiness/status');rows.append(c('api-get-readiness',code==200 and payload.get('data',{}).get('paths_suppressed')))
  try:handle_api_get('/api/release-certification/evidence/select');rejected=False
  except ApiError as exc:rejected=exc.status==404
  rows.append(c('evidence-selection-post-only',rejected))
  html=render_release_certification();rows.append(c('dashboard-content-free',str(base) not in html and 'Certification readiness' in html and 'cannot install, promote' in html and 'contact providers' in html))
  if previous is None:os.environ.pop('EIDOLON_DATA_DIR',None)
  else:os.environ['EIDOLON_DATA_DIR']=previous
 report={'suite':'v1097.1-certification-evidence-intake-readiness-preview','passed':sum(x['ok'] for x in rows),'failed':sum(not x['ok'] for x in rows),'checks':rows};report['ok']=report['failed']==0;print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
