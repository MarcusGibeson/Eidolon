import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from root_cause_analysis import *
from v1363_test_support import *
P=0
req(not analyze_root_cause(source_manifest_digest='bad',reproduction_digest=R,localization_digest=L,facts=FACTS)['ok'],'lineage');P+=1
bad=[dict(FACTS[0],evidence_digest='bad')];req(not analyze_root_cause(source_manifest_digest=S,reproduction_digest=R,localization_digest=L,facts=bad)['ok'],'evidence');P+=1
amb=FACTS+[{'fact_id':'second.root','evidence_digest':'2'*64,'direct_defect_evidence':True,'necessary_for_failure':True}];r=analyze_root_cause(source_manifest_digest=S,reproduction_digest=R,localization_digest=L,facts=amb);req(r['root_cause_analysis']['root_cause_ambiguous'],'ambiguous');P+=1
un=[dict(FACTS[0])];r=analyze_root_cause(source_manifest_digest=S,reproduction_digest=R,localization_digest=L,facts=un);req(not r['root_cause_analysis']['root_cause_resolved'],'unresolved');P+=1
noise=[{'fact_id':'env','evidence_digest':E,'environment_only':True,'direct_defect_evidence':True,'necessary_for_failure':True}];r=analyze_root_cause(source_manifest_digest=S,reproduction_digest=R,localization_digest=L,facts=noise);req(r['root_cause_analysis']['root_defect_count']==0,'env not root');P+=1
req(not r['repair_authorized'],'authority');P+=1
print({'ok':P==6,'passed':P,'total':6,'suite':'v1363.6-8-root-cause-reliability'})
