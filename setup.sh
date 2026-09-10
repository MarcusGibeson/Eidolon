#!/usr/bin/env sh
set -eu

export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON_BIN=${PYTHON_BIN:-}
CORE_ONLY=0
APPLY_UPGRADE_MIGRATION=0

python_compatible() {
  "$1" -c 'import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 15) else 1)' >/dev/null 2>&1
}

select_python() {
  if [ -n "$PYTHON_BIN" ]; then
    if command -v "$PYTHON_BIN" >/dev/null 2>&1 && python_compatible "$PYTHON_BIN"; then
      printf '%s\n' "$PYTHON_BIN"
      return 0
    fi
    echo "PYTHON_BIN must point to Python 3.11, 3.12, 3.13, or 3.14." >&2
    return 1
  fi

  for candidate in python3.11 python3.12 python3.13 python3.14 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && python_compatible "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  echo "Eidolon v1080.0 requires Python 3.11, 3.12, 3.13, or 3.14." >&2
  return 1
}

usage() {
  cat <<'USAGE'
Usage: ./setup.sh [--core-only] [--apply-upgrade-migration]

By default setup only inspects retired sandbox evidence. It never moves evidence
unless --apply-upgrade-migration is explicitly supplied.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --core-only) CORE_ONLY=1 ;;
    --apply-upgrade-migration) APPLY_UPGRADE_MIGRATION=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown setup option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [ ! -x "$ROOT/.venv/bin/python" ]; then
  PYTHON_BIN=$(select_python)
  echo "Creating virtual environment with $PYTHON_BIN..."
  "$PYTHON_BIN" -m venv "$ROOT/.venv"
fi

PY="$ROOT/.venv/bin/python"
if ! python_compatible "$PY"; then
  echo "Existing .venv uses unsupported Python. Eidolon v1080.0 requires Python 3.11, 3.12, 3.13, or 3.14." >&2
  exit 1
fi
"$PY" -m pip install --upgrade pip
if [ "$CORE_ONLY" -eq 1 ]; then
  "$PY" -m pip install -r "$ROOT/requirements-core.txt"
else
  "$PY" -m pip install -r "$ROOT/requirements.txt"
fi

printf '\n'
if [ "$APPLY_UPGRADE_MIGRATION" -eq 1 ]; then
  echo "Explicit migration opt-in supplied. Applying reversible retired-evidence quarantine..."
  "$PY" "$ROOT/tools/upgrade_migrate.py" --apply
else
  echo "Inspecting retired sandbox evidence without changing it..."
  "$PY" "$ROOT/tools/upgrade_migrate.py"
  echo "Migration was NOT applied. Review the inspection above."
  echo "To opt in, rerun setup with --apply-upgrade-migration or run:"
  echo "  .venv/bin/python eidolon.py upgrade-migrate --apply"
fi

"$PY" "$ROOT/tools/release_verify.py" --profile quick
printf '\nReady. Useful commands:\n'
printf '  ./run_eidolon.sh                 # opens the conversation-first dashboard\n'
printf '  .venv/bin/python eidolon.py status\n'
printf '  .venv/bin/python eidolon.py chat\n'
printf '  .venv/bin/python eidolon.py dashboard --open-browser\n'
printf '  .venv/bin/python eidolon.py runtime-guide\n'
printf '  .venv/bin/python eidolon.py startup-soak --runs 5 --json\n'
printf '  .venv/bin/python eidolon.py verify --full\n'
