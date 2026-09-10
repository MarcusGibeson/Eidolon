import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from repair_proposal import *
from v1364_test_support import *
P=0
req(not propose_repair(source_manifest_digest='bad',root_cause_digest=R,root_cause_resolved=True,root_cause_ambiguous=False,candidates=C)['ok'],'lineage');P+=1
r=propose_repair(source_manifest_digest=S,root_cause_digest=R,root_cause_resolved=False,root_cause_ambiguous=False,candidates=C);req(r['repair_proposal']['deferred'],'unresolved');P+=1
r=propose_repair(source_manifest_digest=S,root_cause_digest=R,root_cause_resolved=True,root_cause_ambiguous=True,candidates=C);req(r['repair_proposal']['deferred'],'ambiguous');P+=1
bad=[dict(C[0],rollback_defined=False)];r=propose_repair(source_manifest_digest=S,root_cause_digest=R,root_cause_resolved=True,root_cause_ambiguous=False,candidates=bad);req(r['repair_proposal']['deferred'],'rollback');P+=1
bad=[dict(C[0],addresses_root_cause=False)];r=propose_repair(source_manifest_digest=S,root_cause_digest=R,root_cause_resolved=True,root_cause_ambiguous=False,candidates=bad);req(r['repair_proposal']['deferred'],'root');P+=1
req(not r['repair_execution_authorized'],'authority');P+=1
print({'ok':P==6,'passed':P,'total':6,'suite':'v1364.6-8-repair-proposal-reliability'})
