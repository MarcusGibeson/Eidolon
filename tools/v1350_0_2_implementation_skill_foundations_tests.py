from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from implementation_skill_benchmark import *
from v1350_implementation_skill_test_support import synthetic_good
def main():
 p=0
 def req(v):nonlocal p;assert v;p+=1
 e=evaluate_implementation_skill_evidence(synthetic_good());req(e['all_required_scenarios_passed']);req(e['passed_scenario_count']==6);req(e['missing_scenarios']==[] and e['duplicate_scenarios']==[]);req(len(e['benchmark_digest'])==64)
 print({'ok':True,'suite':'v1350.0-2-implementation-skill-foundations','passed':p,'total':4})
if __name__=='__main__':main()
