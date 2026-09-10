import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from v1451_1488_test_support import run_version_suite
print(run_version_suite(1463,'foundations'))
