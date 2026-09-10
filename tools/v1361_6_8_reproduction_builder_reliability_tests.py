import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from reproduction_builder import *
from v1361_test_support import *
P=0
req(not build_reproduction(source_manifest_digest='bad',evidence_inputs=EVID,candidates=CANDS,environment_digest=ENV)['ok'],'lineage');P+=1
bad=[dict(EVID[0],kind='prompt')];req(not build_reproduction(source_manifest_digest=S,evidence_inputs=bad,candidates=CANDS,environment_digest=ENV)['ok'],'evidence');P+=1
bad=[dict(CANDS[0])];bad[0]['steps']=[{'kind':'shell','target_id':'x'}];req(not build_reproduction(source_manifest_digest=S,evidence_inputs=EVID,candidates=bad,environment_digest=ENV)['ok'],'step');P+=1
none=[dict(CANDS[0],reproduces=False,environment_specific=True)];r=build_reproduction(source_manifest_digest=S,evidence_inputs=EVID,candidates=none,environment_digest=ENV);req(r['ok'] and not r['reproduction']['reproduction_found'],'not found');P+=1;req(r['reproduction']['environment_dependent'],'environment');P+=1
nondet=[dict(CANDS[1],deterministic=False)];r=build_reproduction(source_manifest_digest=S,evidence_inputs=EVID,candidates=nondet,environment_digest=ENV);req(not r['reproduction']['reproduction_found'],'nondeterministic');P+=1
print({'ok':P==6,'passed':P,'total':6,'suite':'v1361.6-8-reproduction-builder-reliability'})
