#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

if __name__ == "__main__":
    # Use the virtual environment Python executable
    venv_python = Path(__file__).parent / ".venv" / "Scripts" / "python.exe"
    script_path = Path(__file__).parent / "scripts" / "partner.py"
    subprocess.run([str(venv_python), str(script_path)] + sys.argv[1:])