#!/usr/bin/env python3
"""
Simple onboarding wrapper script.
Usage: python onboard.py TICKET_ID [--dry-run]
"""

import sys
import subprocess
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python onboard.py TICKET_ID [--dry-run]")
        print("Example: python onboard.py 65030")
        print("Example: python onboard.py 65030 --dry-run")
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
        "onboard", "run", 
        "--ticket-id", ticket_id
    ]
    
    if not dry_run:
        cmd.append("--no-dry-run")
    
    print(f"Running onboarding for ticket {ticket_id} {'(DRY RUN)' if dry_run else '(PRODUCTION)'}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # Execute the command
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\nOnboarding cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error running onboarding: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
