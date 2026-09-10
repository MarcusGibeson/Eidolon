import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from repair_proposal import *
from v1364_test_support import *
P=0;r=propose_repair(source_manifest_digest=S,root_cause_digest=R,root_cause_resolved=True,root_cause_ambiguous=False,candidates=C);req(r['ok'],'ok');P+=1;v=r['repair_proposal'];req(v['proposal_ready'],'ready');P+=1;req(v['selected']['changed_file_count']==1,'narrow');P+=1;req(v['selected']['test_count']==2 and v['selected']['rollback_defined'],'verify');P+=1;req(not r['repair_execution_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1364.0-2-repair-proposal-foundations'})
