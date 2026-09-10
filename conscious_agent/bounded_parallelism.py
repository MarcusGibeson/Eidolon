from __future__ import annotations
"""v1374 bounded parallel execution lanes without authority expansion."""
import hashlib, json, re, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Mapping, Sequence

CONTRACT_VERSION="v1374.8"
DENIED={"execution_authority_created":False,"project_mutation_authorized":False,"source_mutation_authorized":False,"network_authorized":False,"release_authorized":False,"independent_authority_granted":False}

def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()

def _normalize(tasks:Sequence[Mapping[str,Any]],max_parallel:int,cpu_budget:int,memory_budget_mb:int):
    if not tasks or len(tasks)>256 or not(1<=max_parallel<=32) or cpu_budget<1 or memory_budget_mb<1:return None,"parallel_contract_invalid"
    rows=[];seen=set()
    for raw in tasks:
        tid=str(raw.get("task_id") or "")
        if not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,120}",tid) or tid in seen:return None,"parallel_task_identity_invalid"
        seen.add(tid);kind=str(raw.get("kind") or "read")
        if kind not in {"read","test","mutation"}:return None,"parallel_task_kind_invalid"
        reads={str(x) for x in raw.get("reads",[]) if str(x)};writes={str(x) for x in raw.get("writes",[]) if str(x)}
        if kind!="mutation" and writes:return None,"parallel_write_requires_mutation_kind"
        cpu=int(raw.get("cpu_units",1));mem=int(raw.get("memory_mb",1))
        if cpu<1 or mem<1 or cpu>cpu_budget or mem>memory_budget_mb:return None,"parallel_task_resource_exceeds_budget"
        rows.append({"id":tid,"kind":kind,"reads":reads,"writes":writes,"cpu":cpu,"mem":mem,"execution_authorized":raw.get("execution_authorized") is True})
    return rows,None

def _conflict(a,b):
    if a["kind"]=="mutation" or b["kind"]=="mutation":
        return bool(a["writes"] & (b["reads"]|b["writes"]) or b["writes"] & (a["reads"]|a["writes"]) or a["kind"]=="mutation" or b["kind"]=="mutation")
    return False

def _lanes(rows,max_parallel,cpu_budget,memory_budget_mb):
    lanes=[]
    for row in rows:
        placed=False
        if row["kind"]!="mutation":
            for lane in lanes:
                if len(lane)>=max_parallel:continue
                if any(x["kind"]=="mutation" or _conflict(row,x) for x in lane):continue
                if sum(x["cpu"] for x in lane)+row["cpu"]>cpu_budget:continue
                if sum(x["mem"] for x in lane)+row["mem"]>memory_budget_mb:continue
                lane.append(row);placed=True;break
        if not placed:lanes.append([row])
    return lanes

def build_bounded_parallel_plan(*,campaign_record_digest:str,tasks:Sequence[Mapping[str,Any]],max_parallel:int=4,cpu_budget:int=4,memory_budget_mb:int=1024)->dict[str,Any]:
    if not re.fullmatch(r"[a-f0-9]{64}",str(campaign_record_digest or "")):return {"ok":False,"status":"campaign_lineage_required","action_executed":False,**DENIED}
    rows,err=_normalize(tasks,max_parallel,cpu_budget,memory_budget_mb)
    if err:return {"ok":False,"status":err,"action_executed":False,**DENIED}
    lanes=_lanes(rows,max_parallel,cpu_budget,memory_budget_mb)
    public=[]
    for i,lane in enumerate(lanes):
        public.append({"lane_index":i+1,"task_digests":[_d(x["id"]) for x in lane],"task_count":len(lane),"parallel":len(lane)>1,"cpu_units":sum(x["cpu"] for x in lane),"memory_mb":sum(x["mem"] for x in lane),"contains_mutation":any(x["kind"]=="mutation" for x in lane)})
    rec={"contract_version":CONTRACT_VERSION,"campaign_record_digest":campaign_record_digest,"task_count":len(rows),"lane_count":len(public),"max_parallel":max_parallel,"cpu_budget":cpu_budget,"memory_budget_mb":memory_budget_mb,"lanes":public,"all_mutations_serialized":all(not l["contains_mutation"] or l["task_count"]==1 for l in public),"content_free":True,"read_only_plan":True,"action_executed":False,**DENIED}
    rec["record_digest"]=_d(rec)
    return {"ok":True,"status":"bounded_parallel_plan_ready","parallel_plan":rec,"action_executed":False,**DENIED}

def run_bounded_parallel(*,campaign_record_digest:str,tasks:Sequence[Mapping[str,Any]],runner:Callable[[str],Any],max_parallel:int=4,cpu_budget:int=4,memory_budget_mb:int=1024)->dict[str,Any]:
    plan=build_bounded_parallel_plan(campaign_record_digest=campaign_record_digest,tasks=tasks,max_parallel=max_parallel,cpu_budget=cpu_budget,memory_budget_mb=memory_budget_mb)
    if not plan.get("ok"):return plan
    rows,_=_normalize(tasks,max_parallel,cpu_budget,memory_budget_mb)
    assert rows is not None
    if any(not x["execution_authorized"] for x in rows):return {"ok":False,"status":"per_task_execution_authority_required","parallel_plan":plan["parallel_plan"],"action_executed":False,**DENIED}
    lanes=_lanes(rows,max_parallel,cpu_budget,memory_budget_mb);results=[];started=time.monotonic()
    for lane in lanes:
        lane_results=[]
        if len(lane)==1:
            x=lane[0]
            try: value=runner(x["id"]); lane_results.append((x,True,value))
            except Exception as e: lane_results.append((x,False,type(e).__name__))
        else:
            with ThreadPoolExecutor(max_workers=len(lane)) as ex:
                fut={ex.submit(runner,x["id"]):x for x in lane}
                for f in as_completed(fut):
                    x=fut[f]
                    try:lane_results.append((x,True,f.result()))
                    except Exception as e:lane_results.append((x,False,type(e).__name__))
        for x,ok,value in lane_results:
            results.append({"task_id_digest":_d(x["id"]),"ok":ok,"result_digest":_d(value),"mutation":x["kind"]=="mutation"})
        if not all(x[1] for x in lane_results):break
    ok=len(results)==len(rows) and all(x["ok"] for x in results)
    rec={"contract_version":CONTRACT_VERSION,"plan_record_digest":plan["parallel_plan"]["record_digest"],"result_count":len(results),"results":sorted(results,key=lambda x:x["task_id_digest"]),"all_tasks_completed":ok,"elapsed_millis":int((time.monotonic()-started)*1000),"result_content_free":True,"execution_used_preexisting_task_authority":True,"execution_authority_created":False,"action_executed":True,"project_mutation_authorized":False,"source_mutation_authorized":False,"network_authorized":False,"release_authorized":False,"independent_authority_granted":False}
    rec["record_digest"]=_d(rec)
    return {"ok":ok,"status":"bounded_parallel_execution_complete" if ok else "bounded_parallel_execution_incomplete","parallel_execution":rec,"action_executed":True,**DENIED}

def process_bounded_parallel_control(text:str,*,project_state=None,**_):
    if str(text or '').strip().lower() not in {"show parallel plan","inspect parallel plan","show bounded parallelism"}:return {"active":False}
    rec=dict((project_state or {}).get("parallel_plan") or {})
    return {"active":True,"ok":bool(rec),"status":"parallel_plan_found" if rec else "parallel_plan_missing","parallel_plan":rec,"action_executed":False,**DENIED}
