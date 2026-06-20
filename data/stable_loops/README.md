# Stable supervised loops

Saved v6.8 stable supervised loop records live here.

v6.8 adds follow-up completion reporting and closure cleanup. Use `--stable-loop-followup-completion-report all` to see unresolved, ready-to-resolve, resolved, and cleanup candidate follow-up chains. Use `--mark-stable-loop-followup-closed stableloop_ID` after resolved follow-up tasks have been reviewed. `/api-info` also now routes correctly in the dashboard because `/api` matching is exact or slash-prefixed.

# Stable supervised loops

Saved v6.7 stable supervised loop records live here.

Stable-loop records can include:

- preflight results
- preview/live work-cycle references
- review status
- audit and rollback notes
- post-run operator checklist and notes
- final decisions: `keep`, `fix_forward`, `rollback`, `needs_review`, or `undecided`
- decision-aware reporting / cleanup metadata
- task-backed decision follow-up links
- follow-up lifecycle resolution metadata

Useful checks:

```powershell
python conscious_agent/main.py --list-stable-loops
python conscious_agent/main.py --show-stable-loop latest --stable-loop-full
python conscious_agent/main.py --stable-loop-followup-lifecycle-summary all
python conscious_agent/main.py --stable-loop-decision-report action_required
```

v6.7 note: follow-up tasks created from stable-loop decisions now show their stable-loop source in task lifecycle views. Once those linked tasks are done or cancelled, use `--resolve-stable-loop-followups stableloop_ID` or `--resolve-task-stable-loop-followup task_ID` to mark the decision follow-up chain resolved, optionally with `--archive-resolved-stable-loop`.


## v6.9 closure-aware guardrails

Stable-loop live runs now check unresolved decision follow-up chains before live advancement. Preview/preflight remains available, but live execution is blocked until follow-up chains are resolved/closed/archived or the operator explicitly uses the closure-guardrail bypass. Use `python conscious_agent/main.py --stable-loop-guardrails` to inspect the current state.
