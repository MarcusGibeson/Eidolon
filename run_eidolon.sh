#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY=${PYTHON_BIN:-python3}
if [ "$#" -eq 0 ]; then
  set -- start
fi
exec "$PY" "$ROOT/eidolon.py" "$@"
