from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from conscious_agent.bounded_research_reasoning import decompose_research_objective,build_source_strategy,select_diverse_sources
checks=[]
def req(v,n):checks.append(n);assert v,n
dec=decompose_research_objective("Compare current public product claims? Explore possible adoption barriers.",freshness="current")
strategy=build_source_strategy(dec)
req(strategy["ok"] and strategy["strategy_count"]==2,"bounded_strategy_per_subquestion")
first=strategy["strategies"][0]
kinds=[x["source_kind"] for x in first["source_categories"]]
req("primary_official" in kinds and "primary_data" in kinds and "reputable_secondary" in kinds,"comparative_strategy_prefers_primary_and_crosscheck_sources")
req(all(x["reason"] for x in first["source_categories"]),"source_categories_record_why_needed")
req(first["avoid_redundant_hosts"] and first["independent_confirmation_preferred"],"redundancy_and_independence_explicit")
candidates=[
 {"public_url":"https://a.example/report","host":"a.example","source_kind":"primary_official","quality_score":1.0},
 {"public_url":"https://a.example/report","host":"a.example","source_kind":"primary_official","quality_score":1.0},
 {"public_url":"https://a.example/second","host":"a.example","source_kind":"primary_official","quality_score":.95},
 {"public_url":"https://b.example/data","host":"b.example","source_kind":"primary_data","quality_score":.9},
 {"public_url":"https://c.example/analysis","host":"c.example","source_kind":"reputable_secondary","quality_score":.82},
]
selected=select_diverse_sources(candidates,limit=3)
req(len(selected)==3 and len({x["public_url"] for x in selected})==3,"duplicate_urls_not_rebrowsed")
req(len({x["source_kind"] for x in selected})==3,"source_types_diversified_before_repeating_kind")
req(strategy["raw_query_text_included"] is False and strategy["raw_objective_included"] is False,"strategy_is_content_minimized")
print(json.dumps({"suite":"v2501.3-source-strategy","ok":True,"passed":len(checks),"failed":0,"checks":checks},sort_keys=True))
