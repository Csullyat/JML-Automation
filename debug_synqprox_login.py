#!/usr/bin/env python3
"""
Debug script to test SynQ Prox login with detailed page analysis
"""

import sys
import os

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from jml_automation.services.synqprox import SynqProxService
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s | %(message)s'
)

def main():
    """Run SynQ Prox debug test"""
    print("Starting SynQ Prox debug test...")
    
    try:
        service = SynqProxService()
        result = service.execute_termination('carltonlee@filevine.com')
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()