import hashlib
import json


def D(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()
    ).hexdigest()


C = "campaign-1"
CR = D("campaign-record")
STEPS = ["s1", "s2", "s3"]


def req(condition, message):
    if not condition:
        raise AssertionError(message)
