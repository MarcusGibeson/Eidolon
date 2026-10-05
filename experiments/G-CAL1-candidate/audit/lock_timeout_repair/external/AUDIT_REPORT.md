# Independent G-CAL1 Audit

BLOCKED. Stopped at first finding; no repair or further product tests.

[
  {
    "name": "boundary:seal/binding tamper event:event",
    "passed": false,
    "severity": "P1",
    "file": "tools/g_cal1_lab.py",
    "line": 25
  }
]

Traceback (most recent call last):
  File "C:\Users\marcu\AppData\Local\Temp\g-cal1-independent-20261004-7b32e6a1\audit.py", line 77, in reject
    action()
  File "C:\Users\marcu\AppData\Local\Temp\g-cal1-independent-20261004-7b32e6a1\audit.py", line 491, in <lambda>
    reject(lambda:q._boundary_records(),'boundary:seal/binding tamper ' + field,'CORRUPTED_OR_UNPARSEABLE_JOURNAL')
                  ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\marcu\Eidolon-g4adj\tools\g_cal1_lab.py", line 155, in _boundary_records
    event_category(self.package.historical.design,p['event'])=='INVALID' and
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\marcu\Eidolon-g4adj\tools\g_extract1_scoring.py", line 237, in event_category
    raise IntegrityError('PROVENANCE_MISMATCH', 'unfrozen event:' + event)
g_extract1_contract.IntegrityError: PROVENANCE_MISMATCH:unfrozen event:UNKNOWN

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\Users\marcu\AppData\Local\Temp\g-cal1-independent-20261004-7b32e6a1\audit.py", line 864, in <module>
    full_review()
  File "C:\Users\marcu\AppData\Local\Temp\g-cal1-independent-20261004-7b32e6a1\audit.py", line 582, in full_review
    boundary_publication(p)
  File "C:\Users\marcu\AppData\Local\Temp\g-cal1-independent-20261004-7b32e6a1\audit.py", line 491, in boundary_publication
    reject(lambda:q._boundary_records(),'boundary:seal/binding tamper ' + field,'CORRUPTED_OR_UNPARSEABLE_JOURNAL')
  File "C:\Users\marcu\AppData\Local\Temp\g-cal1-independent-20261004-7b32e6a1\audit.py", line 79, in reject
    check(event is None or exc.event == event, name + ':event')
  File "C:\Users\marcu\AppData\Local\Temp\g-cal1-independent-20261004-7b32e6a1\audit.py", line 73, in check
    raise AuditBlocker(name)
AuditBlocker: boundary:seal/binding tamper event:event
