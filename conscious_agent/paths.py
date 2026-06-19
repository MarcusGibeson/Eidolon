from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
MEMORY_FILE = DATA_DIR / "memories.json"
THOUGHT_LOG_FILE = DATA_DIR / "thoughts.log"
SELF_FILE = DATA_DIR / "self_model.json"
DESIRES_FILE = DATA_DIR / "desires.json"
OPINIONS_FILE = DATA_DIR / "opinions.json"

DATA_DIR.mkdir(exist_ok=True)
