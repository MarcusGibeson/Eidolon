from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from dependency_selection import *
from v1348_dependency_selection_test_support import *
def main():
 p=0
 def req(v):nonlocal p;assert v;p+=1
 e=evaluate_dependency_candidates([candidate(existing=False,capability_score=.99),candidate(existing=True,capability_score=.8)]);req(e['selection_status']=='selected_existing_dependency');req(e['selected_existing_dependency']);req(e['candidate_count']==2 and e['viable_candidate_count']==2);req(len(e['selected_candidate_digest'])==64);req(not e['dependency_installed'])
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);(root/'pyproject.toml').write_text('[project]\nname="x"\n');r=inspect_dependency_context(root);req(r['dependency_metadata_file_count']==1 and not r['registry_contacted'])
 print({'ok':True,'suite':'v1348.0-2-dependency-selection-foundations','passed':p,'total':6})
if __name__=='__main__':main()
