from __future__ import annotations
"""v1357 performance verification with fixed budgets and hardware-aware evidence."""
import hashlib,json,math,re,statistics,time,tracemalloc,tempfile
from pathlib import Path
from typing import Any,Mapping,Sequence
CONTRACT_VERSION='v1357.8'
METRICS=('startup_ms','first_visible_ms','total_ms','peak_memory_mb','disk_delta_mb','queue_delay_ms','long_session_degradation_ratio')
DENIED={'source_mutation_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False,'budget_mutation_authorized':False}
def _d(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _pct(values,p):
 s=sorted(values);return s[min(len(s)-1,max(0,math.ceil(p*len(s))-1))]
def run_fixed_host_probe(*,sample_count:int=5,runtime_root=None)->dict[str,Any]:
 try:n=int(sample_count)
 except Exception:return {'ok':False,'status':'performance_probe_count_invalid',**DENIED}
 if n<3 or n>20:return {'ok':False,'status':'performance_probe_count_invalid',**DENIED}
 rows=[];root=Path(runtime_root or tempfile.gettempdir()).resolve();root.mkdir(parents=True,exist_ok=True)
 for i in range(n):
  tracemalloc.start();t0=time.perf_counter();first=None;acc=0
  for j in range(6000):
   acc=(acc+j*j)%10000019
   if j==0:first=time.perf_counter()
  total=time.perf_counter()-t0;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
  p=root/f'.v1357_probe_{i}.tmp';before=p.stat().st_size if p.exists() else 0;p.write_bytes(b'x'*4096);after=p.stat().st_size;p.unlink(missing_ok=True)
  q0=time.perf_counter();time.sleep(.001);queue=max(0,time.perf_counter()-q0-.001)
  # Compare a second bounded loop with the first total as a tiny degradation signal.
  s=time.perf_counter();x=0
  for j in range(6000):x=(x+j*j)%10000019
  second=time.perf_counter()-s
  rows.append({'startup_ms':0.0,'first_visible_ms':(first-t0)*1000 if first else 0.0,'total_ms':total*1000,'peak_memory_mb':peak/(1024*1024),'disk_delta_mb':max(0,after-before)/(1024*1024),'queue_delay_ms':queue*1000,'long_session_degradation_ratio':second/max(total,1e-9)})
 return {'ok':True,'status':'fixed_host_probe_complete','sample_count':n,'observations':rows,'host_probe_only':True,'product_performance_certified':False,**DENIED}
def evaluate_performance(*,source_manifest_digest:str,observations:Sequence[Mapping[str,Any]],budgets:Mapping[str,Any],hardware_profile:Mapping[str,Any],evidence_digest:str)->dict[str,Any]:
 if not re.fullmatch(r'[a-f0-9]{64}',str(source_manifest_digest or '')) or not re.fullmatch(r'[a-f0-9]{64}',str(evidence_digest or '')):return {'ok':False,'status':'performance_lineage_required',**DENIED}
 if len(observations)<3 or len(observations)>200:return {'ok':False,'status':'performance_sample_count_invalid',**DENIED}
 hw={k:hardware_profile.get(k) for k in ('cpu_class','memory_gb','storage_class','power_profile')}
 if not hw['cpu_class'] or not hw['storage_class']:return {'ok':False,'status':'hardware_profile_incomplete',**DENIED}
 data={m:[] for m in METRICS}
 try:
  for row in observations:
   for m in METRICS:
    v=float(row[m]);
    if not math.isfinite(v) or v<0:raise ValueError
    data[m].append(v)
  limits={m:float(budgets[m]) for m in METRICS}
  if any(not math.isfinite(x) or x<=0 for x in limits.values()):raise ValueError
 except Exception:return {'ok':False,'status':'performance_observation_or_budget_invalid',**DENIED}
 metrics={};passed=True
 for m,values in data.items():
  med=statistics.median(values);p95=_pct(values,.95);ok=p95<=limits[m];passed=passed and ok
  metrics[m]={'median':round(med,6),'p95':round(p95,6),'budget':limits[m],'headroom_ratio':round((limits[m]-p95)/limits[m],6),'passed':ok}
 rec={'contract_version':CONTRACT_VERSION,'source_manifest_digest':source_manifest_digest,'evidence_digest':evidence_digest,'sample_count':len(observations),'hardware_profile_digest':_d(hw),'metrics':metrics,'all_budgets_passed':passed,'budget_count':len(metrics),'budgets_fixed_for_evaluation':True,'hardware_aware':True,'raw_observations_persisted':False,'content_free':True,'action_executed':False,**DENIED};rec['record_digest']=_d(rec)
 return {'ok':passed,'status':'performance_verification_passed' if passed else 'performance_budget_regression_detected','performance_verification':rec,'action_executed':False,**DENIED}
def process_performance_verification_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show performance verification','inspect performance verification','show performance tests'}:return {'active':False}
 rec=dict((project_state or {}).get('performance_verification') or {});return {'active':True,'ok':bool(rec),'status':'performance_verification_found' if rec else 'performance_verification_missing','performance_verification':rec,'action_executed':False,**DENIED}
