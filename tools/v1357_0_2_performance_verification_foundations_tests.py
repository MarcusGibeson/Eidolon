import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from performance_verification import *
from v1357_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 p=run_fixed_host_probe(sample_count=3,runtime_root=td);req(p['ok'] and len(p['observations'])==3,'probe');P+=1;req(p['host_probe_only'] and not p['product_performance_certified'],'truth');P+=1
r=evaluate_performance(source_manifest_digest=SOURCE,observations=obs(),budgets=B,hardware_profile=HW,evidence_digest=E);req(r['ok'],'eval');P+=1;v=r['performance_verification'];req(v['budget_count']==7 and v['hardware_aware'],'metrics');P+=1;req(not v['raw_observations_persisted'] and not r['budget_mutation_authorized'],'privacy');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1357.0-2-performance-foundations'})
