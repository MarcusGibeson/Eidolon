from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from dependency_selection import *
from v1348_dependency_selection_test_support import *
def main():
 p=0
 def req(v):nonlocal p;assert v;p+=1
 with tempfile.TemporaryDirectory() as td:
  r=create_dependency_selection(candidates=[candidate(existing=True),candidate(existing=False,capability_score=.99)],source_workspace_digest='b'*64,runtime_root=Path(td));row=r['dependency_selection'];req(r['ok']);req(row['selected_existing_dependency']);req(len(row['candidate_evidence_digest'])==64 and len(row['evaluation_digest'])==64);req(not row['raw_candidate_name_exposed'] and not row['dependency_installed']);req(all(not DEPENDENCY_DENIED_AUTHORITY[k] for k in ('network_authorized','dependency_installation_authorized','lockfile_mutation_authorized','release_authorized','independent_authority_granted')))
 print({'ok':True,'suite':'v1348.9-dependency-selection-checkpoint','passed':p,'total':5})
if __name__=='__main__':main()
