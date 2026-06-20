# Work cycle records

Saved lifecycle-aware work-cycle records live here.

As of v6.8, stable supervised loops use work cycles as the action engine, while stable-loop records wrap those cycles with review gates, audit notes, operator decisions, decision-aware follow-up tasks, follow-up lifecycle resolution, and follow-up completion/closure reports.

Useful checks:
```powershell
python conscious_agent/main.py --list-work-cycles
python conscious_agent/main.py --show-work-cycle latest --work-cycle-full
python conscious_agent/main.py --stable-loop-preflight --no-ai-stable-loop
python conscious_agent/main.py --stable-loop-followup-completion-report all
```

# Work cycle records

Saved lifecycle-aware work-cycle records live here.

As of v6.7, stable supervised loops use work cycles as the action engine, while stable-loop records wrap those cycles with review gates, audit notes, operator decisions, decision-aware follow-up tasks, and follow-up lifecycle resolution.

Useful checks:

```powershell
python conscious_agent/main.py --list-work-cycles
python conscious_agent/main.py --show-work-cycle latest --work-cycle-full
python conscious_agent/main.py --stable-loop-preflight --no-ai-stable-loop
python conscious_agent/main.py --stable-loop-followup-lifecycle-summary all
```


## v6.9 closure-aware guardrails

Stable-loop live runs now check unresolved decision follow-up chains before live advancement. Preview/preflight remains available, but live execution is blocked until follow-up chains are resolved/closed/archived or the operator explicitly uses the closure-guardrail bypass. Use `python conscious_agent/main.py --stable-loop-guardrails` to inspect the current state.
