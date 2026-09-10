from concurrency_diagnosis import diagnose_concurrency

def req(x,m):
 if not x: raise AssertionError(m)
CASES={
'duplicate_work':([{'op':'claim','job':'j','worker':'a','generation':1},{'op':'claim','job':'j','worker':'b','generation':1}],['idempotency_key']),
'stale_ownership':([{'op':'claim','job':'j','worker':'a','generation':2},{'op':'complete','job':'j','worker':'a','generation':1}],['generation_compare_and_swap']),
'lock_contention':([{'op':'lock','worker':'a'},{'op':'lock','worker':'b'}],['bounded_lock_timeout']),
'race':([{'op':'read_modify_write','worker':'a','interleaved':True}],['serialized_transition']),
'crash_recovery':([{'op':'claim','job':'j','worker':'a','generation':1},{'op':'owner_crash','job':'j','worker':'a','generation':1}],['orphan_reconcile']),
}
