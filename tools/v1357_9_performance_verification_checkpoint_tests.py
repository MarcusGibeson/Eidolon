import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from performance_verification import *
from v1357_test_support import *
P=0
r=evaluate_performance(source_manifest_digest=SOURCE,observations=obs(12),budgets=B,hardware_profile=HW,evidence_digest=E);v=r['performance_verification'];req(r['ok'],'checkpoint');P+=1
req(all(x['passed'] for x in v['metrics'].values()),'budgets');P+=1
req(v['sample_count']==12 and v['hardware_aware'],'samples');P+=1
req(v['content_free'] and not v['raw_observations_persisted'],'privacy');P+=1
req(not r['release_authorized'] and not r['source_mutation_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1357.9-performance-checkpoint'})
