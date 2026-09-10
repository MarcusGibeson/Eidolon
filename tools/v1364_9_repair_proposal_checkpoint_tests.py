import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from repair_proposal import *
from v1364_test_support import *
P=0;r=propose_repair(source_manifest_digest=S,root_cause_digest=R,root_cause_resolved=True,root_cause_ambiguous=False,candidates=C);v=r['repair_proposal'];req(r['status']=='repair_proposal_ready','checkpoint');P+=1;req(v['selected']['addresses_root_cause'],'root');P+=1;req(v['selected']['rollback_defined'] and v['selected']['test_count']>0,'safe');P+=1;req(v['read_only'] and not v['implementation_performed'],'readonly');P+=1;req(not r['release_authorized'] and not r['source_mutation_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1364.9-repair-proposal-checkpoint'})
