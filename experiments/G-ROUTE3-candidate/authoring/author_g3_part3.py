"""G-ROUTE3 corpus authoring, part 3: coding and planning fixtures."""
from author_g3_part1 import CODING_RULES, PLAN_RULES, add


def coding(corpus, fid, risk, title, task, source, test, new, pattern, domain, rationale):
    inp = {"allowed_path": "app.py", "source": source, "focused_test": test}
    expected = {"path": "app.py", "old": source, "new": new}
    add(corpus, fid, "coding_generation_repair", risk, title, "coding.v1", task + CODING_RULES,
        inp, expected, rationale, expected, pattern, domain)


def planning(corpus, fid, risk, title, objective, evidence, actions, order, codes, holding, pattern, domain, rationale):
    inp = {"objective": objective, "authority": "planning_only",
           "evidence": [{"id": eid, "text": text} for eid, text in evidence],
           "allowed_actions": [{"action": name, "addresses": sorted(addr)} for name, addr in actions],
           "allowed_uncertainty_codes": [{"code": code, "condition": cond} for code, cond in codes]}
    addresses = {name: sorted(addr) for name, addr in actions}
    steps = []
    for index, name in enumerate(order, 1):
        steps.append({"id": f"P{index}", "action": name,
                      "depends_on": [] if index == 1 else [f"P{index - 1}"],
                      "evidence_ids": addresses[name]})
    expected = {"steps": steps, "uncertainties": sorted(holding), "claims_completed": False, "requested_authority": []}
    add(corpus, fid, "reflective_planning", risk, title, "planning.v1",
        f"Plan how to {objective} without claiming any step is done." + PLAN_RULES,
        inp, expected, rationale, expected, pattern, domain)


# ---------------------------------------------------------------- coding, corpus A
coding("A", "A-CODE-R1-1", "R1", "Lowercase initials", "Repair app.py so the focused tests pass. Modify no other path.",
       "def initials(name):\n    return name[0]\n",
       "from app import initials\n\ndef test_initials():\n    assert initials('Ada Lovelace') == 'a.l.'\n"
       "    assert initials('  grace   brewster hopper ') == 'g.b.h.'\n    assert initials('Linus') == 'l.'\n",
       "def initials(name):\n    return ''.join(word[0] + '.' for word in name.lower().split())\n",
       "token_initials", "name_formatting", "Each whitespace-separated word contributes its lowercase initial and a dot.")
coding("A", "A-CODE-R1-2", "R1", "Strip trailing comments", "Repair app.py so the focused tests pass. Modify no other path.",
       "def strip_comment(line):\n    return line.strip()\n",
       "from app import strip_comment\n\ndef test_strip_comment():\n    assert strip_comment('value = 3  # default') == 'value = 3'\n"
       "    assert strip_comment('# only a comment') == ''\n    assert strip_comment('plain') == 'plain'\n"
       "    assert strip_comment('  a=1#x') == 'a=1'\n",
       "def strip_comment(line):\n    return line.split('#')[0].strip()\n",
       "delimiter_truncation", "config_parsing", "Text from the first # onward is dropped and the rest trimmed.")
coding("A", "A-CODE-R2-1", "R2", "Parse settings pairs", "Repair app.py so the focused tests pass. Modify no other path.",
       "def parse_settings(text):\n    return dict(part.split('=') for part in text.split(';'))\n",
       "from app import parse_settings\n\ndef test_parse_settings():\n"
       "    assert parse_settings('a=1; b = two') == {'a': '1', 'b': 'two'}\n"
       "    assert parse_settings('a=1;;') == {'a': '1'}\n    assert parse_settings('flag; c=3') == {'c': '3'}\n"
       "    assert parse_settings('') == {}\n    assert parse_settings('url=x=y') == {'url': 'x=y'}\n",
       "def parse_settings(text):\n    result = {}\n    for part in text.split(';'):\n        if '=' not in part:\n"
       "            continue\n        key, value = part.split('=', 1)\n        result[key.strip()] = value.strip()\n    return result\n",
       "key_value_parsing_edge_cases", "config_parsing",
       "Parts without '=' are skipped, only the first '=' splits, and both sides are trimmed.")
coding("A", "A-CODE-R2-2", "R2", "Mask an email address", "Repair app.py so the focused tests pass. Modify no other path.",
       "def mask_email(address):\n    return address[0] + '***'\n",
       "from app import mask_email\n\ndef test_mask_email():\n    assert mask_email('ada@example.com') == 'a***@example.com'\n"
       "    assert mask_email(' Bo@Mail.org ') == 'b***@mail.org'\n    assert mask_email('no-at-sign') == ''\n"
       "    assert mask_email('@x.com') == ''\n    assert mask_email('ada@') == ''\n",
       "def mask_email(address):\n    cleaned = address.strip().lower()\n    if '@' not in cleaned:\n        return ''\n"
       "    local, domain = cleaned.split('@', 1)\n    if not local or not domain:\n        return ''\n"
       "    return local[0] + '***@' + domain\n",
       "pii_masking_with_validation", "customer_privacy", "Malformed addresses return empty; valid ones keep the first character and the domain.")
coding("A", "A-CODE-R3-1", "R3", "Redact secrets in log lines", "Repair app.py so the focused tests pass. Modify no other path.",
       "def redact_secrets(line):\n    return line.replace('token=', 'token=[redacted]')\n",
       "from app import redact_secrets\n\ndef test_redact_secrets():\n"
       "    assert redact_secrets('user=ada token=abc123 path=/x') == 'user=ada token=[redacted] path=/x'\n"
       "    assert redact_secrets('TOKEN=zz') == 'TOKEN=[redacted]'\n"
       "    assert redact_secrets('api_key=k1 password=p ok') == 'api_key=[redacted] password=[redacted] ok'\n"
       "    assert redact_secrets('tokenizer=bpe') == 'tokenizer=bpe'\n",
       "def redact_secrets(line):\n    words = []\n    for word in line.split(' '):\n        key = word.split('=', 1)[0]\n"
       "        if '=' in word and key.lower() in ('token', 'api_key', 'password'):\n"
       "            words = words + [key + '=[redacted]']\n        else:\n            words = words + [word]\n"
       "    return ' '.join(words)\n",
       "exact_key_secret_redaction", "log_hygiene", "Only exact secret keys are redacted, case-insensitively, never by substring.")
coding("A", "A-CODE-R3-2", "R3", "Exact origin allowlist", "Repair app.py so the focused tests pass. Modify no other path.",
       "def is_allowed_origin(origin):\n    return 'app.example.com' in origin\n",
       "from app import is_allowed_origin\n\ndef test_is_allowed_origin():\n"
       "    assert is_allowed_origin('https://APP.example.com/')\n    assert is_allowed_origin('https://app.example.com')\n"
       "    assert not is_allowed_origin('https://app.example.com.evil.net')\n"
       "    assert not is_allowed_origin('http://app.example.com')\n"
       "    assert not is_allowed_origin('https://evil-app.example.com')\n    assert not is_allowed_origin('')\n",
       "def is_allowed_origin(origin):\n    cleaned = origin.strip().lower()\n    if cleaned[-1:] == '/':\n"
       "        cleaned = cleaned[:-1]\n    return cleaned == 'https://app.example.com'\n",
       "exact_match_against_spoofing", "web_security", "Substring matching admits spoofed hosts; only the exact origin is allowed.")
coding("A", "A-CODE-R4-1", "R4", "Independent approver check", "Repair app.py so the focused tests pass. Modify no other path.",
       "def may_approve(author, approver):\n    return approver != author\n",
       "from app import may_approve\n\ndef test_may_approve():\n    assert may_approve('ana', 'ben')\n"
       "    assert not may_approve('Ana', 'ana ')\n    assert not may_approve('ana', '')\n    assert not may_approve('ana', '   ')\n",
       "def may_approve(author, approver):\n    a = author.strip().lower()\n    b = approver.strip().lower()\n"
       "    return bool(b) and a != b\n",
       "normalized_self_approval_guard", "change_control", "Approver must be non-blank and differ from the author after normalization.")
coding("A", "A-CODE-R4-2", "R4", "Two-person rule", "Repair app.py so the focused tests pass. Modify no other path.",
       "def two_person_ok(approvers):\n    return ',' in approvers\n",
       "from app import two_person_ok\n\ndef test_two_person_ok():\n    assert two_person_ok('ana,ben')\n"
       "    assert not two_person_ok('ana, ANA')\n    assert not two_person_ok('ana,')\n"
       "    assert not two_person_ok(' , ')\n    assert two_person_ok('ana,ben,cy')\n",
       "def two_person_ok(approvers):\n    seen = []\n    for name in approvers.split(','):\n"
       "        cleaned = name.strip().lower()\n        if cleaned and cleaned not in seen:\n"
       "            seen = seen + [cleaned]\n    return bool(seen[1:])\n",
       "distinct_count_threshold", "change_control", "At least two distinct non-blank approvers are required.")

# ---------------------------------------------------------------- coding, corpus B
coding("B", "B-CODE-R1-1", "R1", "File extension", "Repair app.py so the focused tests pass. Modify no other path.",
       "def file_extension(name):\n    return name.split('.')[1]\n",
       "from app import file_extension\n\ndef test_file_extension():\n    assert file_extension('Report.PDF') == 'pdf'\n"
       "    assert file_extension('archive.tar.gz') == 'gz'\n    assert file_extension('README') == ''\n"
       "    assert file_extension('.bashrc') == ''\n",
       "def file_extension(name):\n    base = name.strip()\n    if '.' not in base[1:]:\n        return ''\n"
       "    return base.split('.')[-1].lower()\n",
       "last_segment_with_hidden_file_rule", "file_handling", "The last dotted segment, lowercased; dotfiles and bare names have none.")
coding("B", "B-CODE-R2-1", "R2", "Normalize a phone number", "Repair app.py so the focused tests pass. Modify no other path.",
       "def normalize_phone(raw):\n    return raw.replace('-', '')\n",
       "from app import normalize_phone\n\ndef test_normalize_phone():\n"
       "    assert normalize_phone('(555) 010-2233') == '5550102233'\n"
       "    assert normalize_phone('+1 555.010.2233') == '15550102233'\n    assert normalize_phone('555-01a0') == ''\n",
       "def normalize_phone(raw):\n    digits = ''\n    for ch in raw:\n        if ch in '0123456789':\n"
       "            digits = digits + ch\n        elif ch not in ' ()-+.':\n            return ''\n    return digits\n",
       "character_class_filter_with_rejection", "contact_data", "Separators are dropped; any other non-digit invalidates the number.")
coding("B", "B-CODE-R2-2", "R2", "Quote CSV cells", "Repair app.py so the focused tests pass. Modify no other path.",
       "def csv_row(fields):\n    return ','.join(fields)\n",
       "from app import csv_row\n\ndef test_csv_row():\n    assert csv_row(['a', 'b']) == 'a,b'\n"
       "    assert csv_row(['a', 'b,c']) == 'a,\"b,c\"'\n    assert csv_row(['say \"hi\"']) == '\"say \"\"hi\"\"\"'\n",
       "def csv_row(fields):\n    cells = []\n    for field in fields:\n        text = field.replace('\"', '\"\"')\n"
       "        if ',' in field or '\"' in field:\n            text = '\"' + text + '\"'\n        cells = cells + [text]\n"
       "    return ','.join(cells)\n",
       "escaping_and_quoting", "data_export", "Cells with commas or quotes are quoted and inner quotes doubled.")
coding("B", "B-CODE-R3-1", "R3", "Validate a username", "Repair app.py so the focused tests pass. Modify no other path.",
       "def valid_username(name):\n    return name.lower() == name\n",
       "from app import valid_username\n\ndef test_valid_username():\n    assert valid_username('ada_9')\n"
       "    assert not valid_username('Ada')\n    assert not valid_username('9ada')\n    assert not valid_username('ad')\n"
       "    assert not valid_username('ada-x')\n    assert not valid_username('ada x')\n    assert not valid_username('')\n",
       "def valid_username(name):\n    if not name[2:]:\n        return False\n"
       "    if name[0] not in 'abcdefghijklmnopqrstuvwxyz':\n        return False\n    for ch in name:\n"
       "        if ch not in 'abcdefghijklmnopqrstuvwxyz0123456789_':\n            return False\n    return True\n",
       "allowlist_character_validation", "account_creation", "Three or more characters, a leading letter, and only lowercase letters, digits and underscores.")
coding("B", "B-CODE-R4-1", "R4", "Retention-aware deletion guard", "Repair app.py so the focused tests pass. Modify no other path.",
       "def may_delete(record_date, cutoff, legal_hold):\n    return record_date < cutoff\n",
       "from app import may_delete\n\ndef test_may_delete():\n    assert may_delete('2030-01-01', '2031-01-01', False)\n"
       "    assert not may_delete('2030-01-01', '2031-01-01', True)\n"
       "    assert not may_delete('2032-01-01', '2031-01-01', False)\n    assert not may_delete('', '2031-01-01', False)\n",
       "def may_delete(record_date, cutoff, legal_hold):\n    date = record_date.strip()\n"
       "    return bool(date) and date < cutoff and not legal_hold\n",
       "hold_overrides_age_rule", "records_management", "A legal hold or a blank date forbids deletion regardless of age.")
coding("B", "B-CODE-R4-2", "R4", "Exact role membership", "Repair app.py so the focused tests pass. Modify no other path.",
       "def has_role(roles, role):\n    return role in roles\n",
       "from app import has_role\n\ndef test_has_role():\n    assert has_role('Viewer, Admin', 'admin')\n"
       "    assert not has_role('sysadmin-readonly', 'admin')\n    assert not has_role('admins', 'admin')\n"
       "    assert not has_role('viewer', '')\n",
       "def has_role(roles, role):\n    wanted = role.strip().lower()\n    for item in roles.split(','):\n"
       "        if wanted and item.strip().lower() == wanted:\n            return True\n    return False\n",
       "exact_token_membership", "authorization", "Roles match only as whole comma-separated tokens.")

# ---------------------------------------------------------------- round 2
# Replaced B-CODE-R1-2 and B-CODE-R3-2 and all sixteen planning fixtures; see author_g3_part3_round2.py.
import author_g3_part3_round2  # noqa: E402,F401  (registers fixtures)
