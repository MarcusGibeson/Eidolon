# v1388.9 Automatic Self-Rollback Final Validation

v1388.9 can stage and apply a canary-qualified candidate only to an explicitly external installed-source tree under exact operator authorization. Failed post-install health automatically restores the prior source manifest and retains content-free failure evidence. The currently executing Eidolon repository is explicitly rejected as a transaction target.

Focused verification: foundations 5/5; integration 5/5; reliability/adversarial 7/7; checkpoint 5/5.
