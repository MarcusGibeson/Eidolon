import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from fault_localization import *
from v1362_test_support import *
P=0
req(not localize_fault(source_manifest_digest='bad',reproduction_digest=R,candidates=C)['ok'],'lineage');P+=1
bad=[dict(C[0],call_distance=-1)];req(not localize_fault(source_manifest_digest=S,reproduction_digest=R,candidates=bad)['ok'],'distance');P+=1
bad=[dict(C[0],evidence_digests=[])];req(not localize_fault(source_manifest_digest=S,reproduction_digest=R,candidates=bad)['ok'],'evidence');P+=1
tie=[dict(C[1],component_id='a',call_distance=1,state_transition_match=False),dict(C[1],component_id='b',call_distance=1,state_transition_match=False)];r=localize_fault(source_manifest_digest=S,reproduction_digest=R,candidates=tie);req(r['fault_localization']['top_tie_count']==2 and r['fault_localization']['confidence']=='low','tie');P+=1
req(r['fault_localization']['single_cause_asserted'] is False,'no assert');P+=1
req(all('component_id' not in x for x in r['fault_localization']['ranked_candidates']),'hashed');P+=1
print({'ok':P==6,'passed':P,'total':6,'suite':'v1362.6-8-fault-localization-reliability'})
