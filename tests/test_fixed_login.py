#!/usr/bin/env python3
"""Quick test of the fixed SYNQ Prox login with TAB sequence."""

import sys
import os
sys.path.append('src')

from jml_automation.services.synqprox import SynqProxService

def test_fixed_login():
    """Test the fixed login sequence."""
    print("Testing SYNQ Prox login with TAB sequence fix...")
    
    service = SynqProxService()
    
    # Test just the login portion
    if service._setup_driver():
        try:
            result = service._login()
            if result:
                print("SUCCESS: LOGIN SUCCESSFUL!")
                return True
            else:
                print("ERROR: Login failed")
                return False
        finally:
            if service.driver:
                service.driver.quit()
    else:
        print("ERROR: Driver setup failed")
        return False

if __name__ == "__main__":
    success = test_fixed_login()
    print(f"\nTest result: {'SUCCESS' if success else 'FAILED'}")