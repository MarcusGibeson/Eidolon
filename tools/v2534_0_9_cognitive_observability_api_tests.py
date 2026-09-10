from __future__ import annotations
import inspect
from conscious_agent.api_server import handle_api_get

def main():
    checks=[]
    code=inspect.getsource(handle_api_get)
    checks += ['["cognition", "observability"]' in code, 'build_cognitive_observability_snapshot' in code]
    status,payload=handle_api_get('/api/cognition/observability?limit=5')
    checks += [status==200, payload.get('ok') is True]
    data=payload.get('data') if isinstance(payload.get('data'),dict) else payload
    checks += [data.get('authority_boundary',{}).get('read_only') is True, data.get('authority_boundary',{}).get('hidden_reasoning_exposed') is False]
    status2,payload2=handle_api_get('/api/cognition/observability?kind=secret_thought')
    checks += [status2==400, 'unsupported_event_kind' in str(payload2)]
    passed=sum(bool(x) for x in checks)
    print({'passed':passed,'total':len(checks),'checks':[bool(x) for x in checks]})
    raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__': main()
