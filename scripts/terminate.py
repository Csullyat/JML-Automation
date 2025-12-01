#!/usr/bin/env python3
"""
Simple termination wrapper script.
Usage: python terminate.py TICKET_ID [--dry-run]
"""

import sys
import subprocess
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python terminate.py TICKET_ID [--dry-run]")
        print("Example: python terminate.py 67008")
        print("Example: python terminate.py 67008 --dry-run")
        sys.exit(1)
    
    ticket_id = sys.argv[1]
    
    # Check if dry-run is requested
    if len(sys.argv) > 2 and "--dry-run" in sys.argv:
        dry_run = True
    else:
        dry_run = False
    
    # Build the command
    cmd = [
        sys.executable, "-m", "jml_automation.cli.app", 
        "terminate", "run", 
        "--ticket-id", ticket_id
    ]
    
    if not dry_run:
        cmd.append("--production-mode")
    
    print(f"Running termination for ticket {ticket_id} {'(DRY RUN)' if dry_run else '(PRODUCTION)'}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # Execute the command
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\nTermination cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error running termination: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
