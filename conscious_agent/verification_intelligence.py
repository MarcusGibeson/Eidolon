from __future__ import annotations

"""v1496 evidence-bound verification planning and result classification."""

import hashlib, json
from pathlib import PurePosixPath
from typing import Any, Iterable, Mapping

CONTRACT_VERSION='v1496.9'
MANDATORY_SUITES=('python_compile','source_immutability','source_only_privacy')


def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def verification_plan(*,changed_files:Iterable[str],candidate_test_files:Iterable[str]=(),release_suites:Iterable[str]=())->dict[str,Any]:
 changed=sorted({str(x).replace('\\','/') for x in changed_files if str(x).strip()})
 tests=sorted({str(x).replace('\\','/') for x in candidate_test_files if str(x).endswith('.py')})
 suites=list(MANDATORY_SUITES)
 suites.extend(tests)
 if any(PurePosixPath(p).parts and PurePosixPath(p).parts[0]=='conscious_agent' for p in changed):suites.extend(['focused_behavioral','retained_architecture'])
 if any(token in p.casefold() for p in changed for token in ('approval','authority','install','release','provider','privacy')):suites.extend(['security_authority_regression'])
 suites.extend(str(x) for x in release_suites if str(x))
 suites=list(dict.fromkeys(suites))
 row={'contract_version':CONTRACT_VERSION,'changed_file_count':len(changed),'changed_files_digest':_digest(changed),'suite_count':len(suites),'suites':suites,'full_release_wrapper_required':False,'native_windows_required':any(p.casefold().endswith(('.ps1','.bat','.exe')) or 'desktop' in p.casefold() for p in changed),'content_free':True}
 row['verification_plan_digest']=_digest(row);return row

def classify_receipt(receipt:Mapping[str,Any])->str:
 if bool(receipt.get('passed')):return 'pass'
 if bool(receipt.get('timed_out')) and int(receipt.get('assertions_failed') or 0)==0:return 'wrapper_timeout'
 if not bool(receipt.get('provider_available',True)):return 'provider_unavailable'
 if bool(receipt.get('baseline_same')):return 'stale_fixture_or_inherited_failure'
 if bool(receipt.get('cleanup_dirty')):return 'dirty_runtime_fixture'
 if bool(receipt.get('certification_only')):return 'optional_certification_failure'
 return 'product_failure'

def evaluate_verification(plan:Mapping[str,Any],receipts:Iterable[Mapping[str,Any]])->dict[str,Any]:
 rows=[dict(r or {}) for r in receipts];classes=[classify_receipt(r) for r in rows]
 product_failures=classes.count('product_failure')
 required_names=set(plan.get('suites') or ());seen={str(r.get('suite') or '') for r in rows if bool(r.get('passed'))}
 missing=sorted(x for x in required_names if x not in seen)
 result={'contract_version':CONTRACT_VERSION,'receipt_count':len(rows),'classification_counts':{c:classes.count(c) for c in sorted(set(classes))},'product_failure_count':product_failures,'missing_required_suites':missing,'verification_passed':product_failures==0 and not missing,'source_install_authorized':False,'promotion_authorized':False,'automatic_retry':False,'content_free':True}
 result['verification_digest']=_digest({'plan':plan.get('verification_plan_digest'),'classes':classes,'seen':sorted(seen),'missing':missing});return result

__all__=['CONTRACT_VERSION','verification_plan','classify_receipt','evaluate_verification']
