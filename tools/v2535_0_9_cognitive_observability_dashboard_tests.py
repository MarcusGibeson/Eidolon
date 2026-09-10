from __future__ import annotations
import inspect
from conscious_agent import dashboard

def main():
    checks=[]
    html=dashboard.render_cognitive_observability_dashboard()
    checks += [
        'Cognitive observability' in html,
        '/api/cognition/observability' in html,
        'This is not hidden chain-of-thought' in html,
        'Read-only projection' in html,
        'mind-recent' in html,
        'mind-trends' in html,
        'setInterval(loadMind,5000)' in html,
    ]
    src=inspect.getsource(dashboard)
    checks += [
        'path == "/cognitive-observability"' in src,
        'render_cognitive_observability_dashboard()' in src,
        '("/cognitive-observability", "Mind"' in src,
    ]
    passed=sum(bool(x) for x in checks)
    print({'passed':passed,'total':len(checks),'checks':[bool(x) for x in checks]})
    raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__': main()
