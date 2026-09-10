import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from reproduction_builder import *
from v1361_test_support import *
P=0;r=build_reproduction(source_manifest_digest=S,evidence_inputs=EVID,candidates=CANDS,environment_digest=ENV);v=r['reproduction'];req(r['ok'],'checkpoint');P+=1;req(v['step_count']==3 and v['reproduction_found'],'minimal');P+=1;req(v['content_free'] and v['read_only'],'privacy');P+=1;req(v['environment_digest']==ENV,'environment');P+=1;req(not r['release_authorized'] and not r['source_mutation_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1361.9-reproduction-builder-checkpoint'})
