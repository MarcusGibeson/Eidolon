from __future__ import annotations
"""v2615 read-only project dependency/resource conflict inspection."""
from typing import Any, Mapping, Sequence
import hashlib,json,collections
CONTRACT_VERSION='v2615.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def inspect_portfolio_conflicts(rows:Sequence[Mapping[str,Any]])->dict[str,Any]:
 deps={str(r.get('project_id')):set(map(str,r.get('depends_on') or [])) for r in rows if isinstance(r,Mapping) and r.get('project_id')}; resources=collections.defaultdict(list)
 for r in rows:
  if not isinstance(r,Mapping) or not r.get('project_id'):continue
  for x in r.get('exclusive_resources') or []:resources[str(x)[:120]].append(str(r.get('project_id'))[:120])
 conflicts=[{'resource':k,'project_ids':sorted(v)} for k,v in sorted(resources.items()) if len(v)>1]
 missing=[];ids=set(deps)
 for p,ds in deps.items():
  for d in sorted(ds):
   if d not in ids:missing.append({'project_id':p,'missing_dependency':d})
 # bounded cycle detection
 visiting=set();done=set();cycles=[]
 def walk(n,path):
  if n in visiting:
   cyc=path[path.index(n):]+[n] if n in path else [n,n];cycles.append(cyc);return
  if n in done:return
  visiting.add(n)
  for d in deps.get(n,set()):
   if d in deps:walk(d,path+[n])
  visiting.discard(n);done.add(n)
 for n in sorted(deps):walk(n,[])
 out={'ok':True,'contract_version':CONTRACT_VERSION,'resource_conflicts':conflicts[:16],'missing_dependencies':missing[:16],'dependency_cycles':cycles[:8],'conflict_count':len(conflicts)+len(missing)+len(cycles),'portfolio_modified':False,'project_removed':False,'campaign_started':False,'authority_granted':False};out['conflict_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','inspect_portfolio_conflicts']
