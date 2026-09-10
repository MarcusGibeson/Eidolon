from __future__ import annotations
"""v1308 standing-session budget accounting."""
from typing import Mapping
from cognitive_coding_foundations import DENIED_AUTHORITY,digest
CONTRACT_VERSION='v1308.8';FIELDS=('elapsed_seconds','tokens','cpu_seconds','memory_mb_peak','disk_mb','commands','retries','files_changed','network_requests')
def create_budget(limits:Mapping[str,int]):
 lim={k:max(0,int(limits.get(k,0))) for k in FIELDS};row={'contract_version':CONTRACT_VERSION,'limits':lim,'used':{k:0 for k in FIELDS},'exhausted':False,'budget_grants_authority':False,**DENIED_AUTHORITY};row['budget_digest']=digest(row);return row
def consume_budget(budget:Mapping,delta:Mapping[str,int]):
 row={**budget,'limits':dict(budget.get('limits') or {}),'used':dict(budget.get('used') or {})};ex=[]
 for k in FIELDS:row['used'][k]=max(0,int(row['used'].get(k,0))+max(0,int(delta.get(k,0))));limit=int(row['limits'].get(k,0));ex += [k] if limit>=0 and row['used'][k]>limit else []
 row['exhausted']=bool(ex);row['exhausted_fields']=ex;row['budget_digest']=digest({k:v for k,v in row.items() if k!='budget_digest'});return row
__all__=['CONTRACT_VERSION','FIELDS','create_budget','consume_budget']
