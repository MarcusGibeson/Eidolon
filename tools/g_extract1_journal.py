"""Write-once hash-chain evidence and deterministic sealed checkpoints."""
from __future__ import annotations

import json
import os
from pathlib import Path

from g_extract1_contract import canonical, digest, load, require, IntegrityError

SCHEMA = dict(journal='g-extract1.call-journal.v2', checkpoint='g-extract1.checkpoint.v2',
              serialization='UTF-8 compact sorted-key JSON; no newline',
              journal_record='sequence,previous_sha256,payload,sha256',
              checkpoint_envelope='payload,sha256',
              durability='exclusive create; flush and fsync; no replace or truncate',
              lineage='CHECKPOINT_CREATED binds sealed pre-marker prefix; RESUME_VERIFIED binds latest marker and retains INCOMPLETE')


def write_once(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('xb') as stream:
            stream.write(canonical(value))
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise IntegrityError('PROVENANCE_MISMATCH', 'write-once collision:' + path.name)


class Journal:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def read(self):
        paths = sorted(self.directory.glob('*.json'))
        records, previous = [], '0' * 64
        for index, path in enumerate(paths, 1):
            require(path.name == f'{index:06d}.json', 'CORRUPTED_OR_UNPARSEABLE_JOURNAL', 'sequence gap')
            try:
                raw = path.read_bytes()
                def unique(items):
                    result = {}
                    for key, value in items:
                        require(key not in result, 'CORRUPTED_OR_UNPARSEABLE_JOURNAL', 'duplicate key')
                        result[key] = value
                    return result
                row = json.loads(raw, object_pairs_hook=unique)
                require(type(row) is dict and set(row) == {'sequence','previous_sha256','payload','sha256'}, 'CORRUPTED_OR_UNPARSEABLE_JOURNAL', 'shape')
                seal = {k:v for k,v in row.items() if k != 'sha256'}
                require(row['sequence'] == index and row['previous_sha256'] == previous and
                        row['sha256'] == digest(canonical(seal)) and raw == canonical(row),
                        'CORRUPTED_OR_UNPARSEABLE_JOURNAL', 'hash chain')
            except (ValueError, KeyError, UnicodeError, TypeError) as exc:
                raise IntegrityError('CORRUPTED_OR_UNPARSEABLE_JOURNAL', type(exc).__name__)
            previous = row['sha256']
            records.append(row)
        return records

    def append(self, payload):
        records = self.read()
        sealed = dict(sequence=len(records)+1, previous_sha256=records[-1]['sha256'] if records else '0'*64,
                      payload=payload)
        sealed['sha256'] = digest(canonical(sealed))
        write_once(self.directory / f'{len(records)+1:06d}.json', sealed)
        return sealed

    def prefix(self, records=None):
        records = self.read() if records is None else records
        return dict(record_count=len(records), last_sha256=records[-1]['sha256'] if records else '0'*64)


def checkpoint_payload(run_id, binding, schedule, journal, next_position, state, *, prefix=None):
    return dict(schema_version=SCHEMA['checkpoint'], run_id=run_id, frozen_binding=binding,
                schedule_sha256=digest(canonical(schedule)), journal_prefix=journal.prefix() if prefix is None else prefix,
                next_schedule_position=next_position, state=state)


def seal_checkpoint(path, payload):
    row = dict(payload=payload, sha256=digest(canonical(payload)))
    write_once(path, row)
    return row


def verify_checkpoint(path, *, run_id, binding, schedule, journal, reconstructed_state, next_position, prefix=None):
    path = Path(path)
    require(path.is_file(), 'MISSING_CHECKPOINT_AFTER_INTERRUPTION')
    try:
        row = load(path)
        require(set(row) == {'payload','sha256'} and row['sha256'] == digest(canonical(row['payload'])) and
                path.read_bytes() == canonical(row), 'CORRUPTED_CHECKPOINT')
    except (ValueError, KeyError, UnicodeError, TypeError) as exc:
        raise IntegrityError('CORRUPTED_CHECKPOINT', type(exc).__name__)
    payload = row['payload']
    actual_prefix = journal.prefix() if prefix is None else prefix
    require(payload.get('journal_prefix') == actual_prefix, 'UNVERIFIABLE_JOURNAL_PREFIX')
    expected = checkpoint_payload(run_id, binding, schedule, journal, next_position, reconstructed_state, prefix=actual_prefix)
    require(payload == expected, 'UNVERIFIABLE_INTERRUPTION_CHECKPOINT', 'state/schedule/next-position/binding')
    return row
