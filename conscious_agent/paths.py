from pathlib import Path

from runtime_data_bootstrap import ensure_runtime_data_env

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ensure_runtime_data_env()
MEMORY_FILE = DATA_DIR / "memories.json"
THOUGHT_LOG_FILE = DATA_DIR / "thoughts.log"
SELF_FILE = DATA_DIR / "self_model.json"
DESIRES_FILE = DATA_DIR / "desires.json"
OPINIONS_FILE = DATA_DIR / "opinions.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)


def relative_path(path: str | Path) -> Path:
    """Return a stable project/data-relative reference for reports and receipts."""
    candidate = Path(path).resolve()
    try:
        return candidate.relative_to(ROOT_DIR.resolve())
    except ValueError:
        try:
            return Path("data") / candidate.relative_to(DATA_DIR.resolve())
        except ValueError:
            return candidate


def path_reference(path: str | Path) -> str:
    return relative_path(path).as_posix()


def resolve_path_reference(value: str | Path) -> Path:
    reference = Path(value)
    if reference.is_absolute():
        return reference.resolve()
    parts = reference.parts
    if parts and parts[0].lower() == "data":
        return (DATA_DIR.joinpath(*parts[1:])).resolve()
    return (ROOT_DIR / reference).resolve()
