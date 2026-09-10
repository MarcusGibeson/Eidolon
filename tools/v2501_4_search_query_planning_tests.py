from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from conscious_agent.bounded_research_reasoning import decompose_research_objective,build_source_strategy,plan_public_search_queries,sanitize_public_query
checks=[]
def req(v,n):checks.append(n);assert v,n
private="Compare my wife Melissa's browser notes from C:\\Users\\Marcus\\private\\notes.txt with current public browser security research; contact marcus@example.com api_key=abcdef1234567890"
safe=sanitize_public_query(private)
for forbidden in ("melissa","marcus","wife","users","private","notes.txt","example.com","api_key","abcdef1234567890"):
 req(forbidden not in safe.casefold(),f"private_shape_removed_{forbidden.replace('.','_')}")
req("browser" in safe and "security" in safe,"useful_public_terms_retained")
dec=decompose_research_objective(private,freshness="current")
strategy=build_source_strategy(dec)
plan=plan_public_search_queries(private,dec,strategy,max_queries=2)
req(plan["ok"] and plan["query_count"]<=2,"hard_query_count_respected")
req(all(x["private_context_removed"] for x in plan["queries"]),"queries_mark_private_context_removed")
req(all("query" not in x for x in plan["public_summary"]),"durable_public_summary_excludes_query_text")
req(plan["credentials_retained"] is False and plan["local_paths_retained"] is False and plan["private_names_retained_by_policy"] is False,"privacy_contract_explicit")
empty=decompose_research_objective("Melissa C:\\Users\\Marcus\\private",freshness="current")
empty_plan=plan_public_search_queries("Melissa C:\\Users\\Marcus\\private",empty,build_source_strategy(empty),max_queries=1)
req(not empty_plan["ok"],"planner_fails_closed_when_no_safe_public_query_remains")
print(json.dumps({"suite":"v2501.4-search-query-planning","ok":True,"passed":len(checks),"failed":0,"checks":checks},sort_keys=True))
