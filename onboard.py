#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

if __name__ == "__main__":
    script_path = Path(__file__).parent / "scripts" / "onboard.py"
    subprocess.run([sys.executable, str(script_path)] + sys.argv[1:])
