from __future__ import annotations
import os,sys,tempfile,shutil,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AGENT=ROOT/'conscious_agent';R=Path(tempfile.mkdtemp(prefix='eidolon-v1489-b18-'))
os.environ['EIDOLON_DATA_DIR']=str(R/'runtime');os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True;sys.path.insert(0,str(AGENT))
from verification_evidence_quality import *
P=F=0
def ck(n,c,d=''):
 global P,F
 if c:P+=1;print('PASS',n)
 else:F+=1;print('FAIL',n,d);raise AssertionError(d or n)
try:
 rv=(ROOT/'tools/release_verify.py').read_text(); paths=re.findall(r'\("v1489-browser-b\d+", "([^"]+)"\)',rv); ck('0171 focused suite inventory registered exactly once',len(paths)==20 and len(paths)==len(set(paths)),paths)
 ck('0171 all registered focused suites exist',all((ROOT/p).exists() for p in paths),[p for p in paths if not (ROOT/p).exists()])
 # Behavioral contract replaces source-shape logic: classification uses outcomes/baseline evidence.
 ck('0172 stale fixture classified behaviorally',classify_verification_failure(return_code=1,assertions_failed=1,baseline_same=True)=='stale_fixture')
 classes=[classify_verification_failure(return_code=1,timed_out=True),classify_verification_failure(return_code=1,provider_available=False),classify_verification_failure(return_code=1,cleanup_dirty=True),classify_verification_failure(return_code=1,certification_only=True),classify_verification_failure(return_code=1)]
 ck('0173 failure classes distinct',classes==['wrapper_timeout','provider_unavailable','environmental_cleanup','optional_certification','product_defect'],classes)
 rec=synthetic_record(record_id='fixture-1',provenance='user');ck('0174 deterministic test factory explicit provenance',rec['synthetic'] and rec['provenance']=='user' and len(rec['content_digest'])==64,rec)
 receipt=verification_receipt(suite='synthetic',passed=7,failed=0,duration_ms=12);ck('0175 standardized content-free verification receipt',receipt['content_free'] and len(receipt['receipt_digest'])==64 and 'PRIVATE' not in str(receipt),receipt)
 par=parity_receipt({'state':'ok','count':1},{'state':'ok','count':1},['state','count']);ck('0176 streaming/nonstream parity receipt',par['parity'] and par['mismatch_count']==0,par)
 sample=R/'source';sample.mkdir();(sample/'a.py').write_text('x=1\n');before=source_snapshot(sample);after=source_snapshot(sample);ck('0177 source immutability helper',immutable(before,after))
 for name in ('short','long','restart'):ck('0178 bounded soak profile '+name,soak_profile(name)['turns']>0 and soak_profile(name)['content_free'],soak_profile(name))
 summary=human_verification_summary([receipt,verification_receipt(suite='two',passed=3,failed=1,duration_ms=1)]);ck('0179 human-readable structured summary','10 checks passed' in summary and '1 checks failed' in summary,summary)
finally:shutil.rmtree(R,ignore_errors=True)
print(f'SUMMARY passed={P} failed={F}');raise SystemExit(1 if F else 0)
