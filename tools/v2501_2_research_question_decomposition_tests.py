from __future__ import annotations
import json, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT)); sys.dont_write_bytecode=True
from conscious_agent.bounded_research_reasoning import decompose_research_objective
checks=[]
def req(v,n): checks.append(n); assert v,n
objective="What is the current public status of browser security? Compare browser isolation versus process isolation? What is the current public status of browser security? Explore unresolved evidence gaps."
row=decompose_research_objective(objective,freshness="current")
req(row["ok"] and row["subquestion_count"]==3,"duplicate_subquestions_removed")
kinds=[x["question_kind"] for x in row["subquestions"]]
req(kinds==["current","comparative","exploratory"],"question_kinds_distinguished")
req(all("uncertainty" in x for x in row["subquestions"]) and row["uncertainty_preserved"],"uncertainty_preserved")
req(all("question" not in x for x in row["public_subquestions"]),"public_decomposition_is_digest_only")
req(objective not in json.dumps(row["public_subquestions"]),"raw_objective_absent_from_public_rows")
req(row["non_repetitive"] and len(row["decomposition_digest"])==64,"decomposition_digest_bound")
req(not row["network_contacted"] and not row["authority_expanded"],"planning_does_not_expand_authority")
print(json.dumps({"suite":"v2501.2-research-question-decomposition","ok":True,"passed":len(checks),"failed":0,"checks":checks},sort_keys=True))
