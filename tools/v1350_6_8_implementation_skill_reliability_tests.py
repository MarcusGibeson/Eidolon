from __future__ import annotations
import copy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from implementation_skill_benchmark import *
from v1350_implementation_skill_test_support import synthetic_good
def main():
 p=0
 def req(v):nonlocal p;assert v;p+=1
 good=synthetic_good()
 bad=copy.deepcopy(good);bad[0]['verification_passed']=False;req(not evaluate_implementation_skill_evidence(bad)['all_required_scenarios_passed'])
 bad=copy.deepcopy(good);bad[1]['workspace_cleaned']=False;req(not evaluate_implementation_skill_evidence(bad)['all_required_scenarios_passed'])
 bad=copy.deepcopy(good);bad[2]['selected_source_content_modified']=True;req(not evaluate_implementation_skill_evidence(bad)['all_required_scenarios_passed'])
 bad=copy.deepcopy(good);bad[3]['authority_safe']=False;req(not evaluate_implementation_skill_evidence(bad)['all_required_scenarios_passed'])
 bad=good[:-1];req('dependency_selection' in evaluate_implementation_skill_evidence(bad)['missing_scenarios'])
 bad=good+[dict(good[0])];req('python' in evaluate_implementation_skill_evidence(bad)['duplicate_scenarios'])
 bad=copy.deepcopy(good);bad[0]['evidence_digest']='x';req(not evaluate_implementation_skill_evidence(bad)['all_required_scenarios_passed'])
 req(not IMPLEMENTATION_SKILL_DENIED_AUTHORITY['network_authorized']);req(not IMPLEMENTATION_SKILL_DENIED_AUTHORITY['release_authorized'])
 eid=(ROOT/'eidolon.py').read_text(encoding='utf-8'); ordinary=(ROOT/'conscious_agent/ordinary_chat_development_campaign.py').read_text(encoding='utf-8')
 req('from chat_launcher import main as chat_main' in eid and 'return int(chat_main())' in eid)
 req('normalized_control = text.strip().lower()' in ordinary and ordinary.index('normalized_control = text.strip().lower()') < ordinary.index('from implementation_skill_benchmark import process_implementation_skill_benchmark_control'))
 print({'ok':True,'suite':'v1350.6-8-implementation-skill-reliability','passed':p,'total':11})
if __name__=='__main__':main()
