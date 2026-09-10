from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from dependency_selection import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1348_dependency_selection_test_support import *
def main():
 p=0
 def req(v):nonlocal p;assert v;p+=1
 with tempfile.TemporaryDirectory() as td:
  runtime=Path(td);r=create_dependency_selection(candidates=[candidate(existing=True),candidate(capability_score=.98)],source_workspace_digest='a'*64,runtime_root=runtime);row=r['dependency_selection'];req(r['ok'] and row['selected_existing_dependency']);req(row['selection_status']=='selected_existing_dependency');req(not row['raw_candidate_name_exposed']);chat=process_ordinary_chat_development_turn('show dependency selection',project_state={'dependency_selection_id':row['dependency_selection_id']},runtime_root=runtime);req(chat.get('active') and chat.get('ok') and not chat.get('action_executed'));r2=create_dependency_selection(candidates=[candidate(existing=True),candidate(capability_score=.98)],source_workspace_digest='a'*64,runtime_root=runtime);req(r2['status']=='dependency_selection_already_exists' and not r2['action_executed'])
 print({'ok':True,'suite':'v1348.3-5-dependency-selection-integration','passed':p,'total':5})
if __name__=='__main__':main()
