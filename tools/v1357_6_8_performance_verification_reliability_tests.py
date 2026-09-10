import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from performance_verification import *
from v1357_test_support import *
P=0
req(not evaluate_performance(source_manifest_digest='bad',observations=obs(),budgets=B,hardware_profile=HW,evidence_digest=E)['ok'],'lineage');P+=1
req(not evaluate_performance(source_manifest_digest=SOURCE,observations=obs(2),budgets=B,hardware_profile=HW,evidence_digest=E)['ok'],'samples');P+=1
req(not evaluate_performance(source_manifest_digest=SOURCE,observations=obs(),budgets=B,hardware_profile={'cpu_class':'x'},evidence_digest=E)['ok'],'hardware');P+=1
bad=dict(B);bad['startup_ms']=800;r=evaluate_performance(source_manifest_digest=SOURCE,observations=obs(),budgets=bad,hardware_profile=HW,evidence_digest=E);req(not r['ok'] and not r['performance_verification']['metrics']['startup_ms']['passed'],'regression');P+=1
req(r['performance_verification']['metrics']['startup_ms']['budget']==800,'fixed');P+=1
negative=obs();negative[0]['queue_delay_ms']=-1;req(not evaluate_performance(source_manifest_digest=SOURCE,observations=negative,budgets=B,hardware_profile=HW,evidence_digest=E)['ok'],'negative');P+=1
req(not run_fixed_host_probe(sample_count=2)['ok'],'probe budget');P+=1
req(not r['budget_mutation_authorized'],'authority');P+=1
print({'ok':P==8,'passed':P,'total':8,'suite':'v1357.6-8-performance-reliability'})
