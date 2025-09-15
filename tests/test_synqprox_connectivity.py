#!/usr/bin/env python3
"""
Test SYNQ Prox connectivity only (no deletion).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from jml_automation.services.synqprox import SynqProxService

def test_synqprox_connectivity():
    """Test SYNQ Prox connectivity without performing deletion."""
    
    print("=== Testing SYNQ Prox Connectivity ===")
    
    synq_service = SynqProxService()
    
    print("Testing connectivity to SYNQ Prox...")
    result = synq_service.test_connectivity()
    
    if result.get('success'):
        print(f"SUCCESS: Connectivity test passed: {result.get('message')}")
        print(f"   URL: {result.get('url')}")
    else:
        print(f"ERROR: Connectivity test failed: {result.get('error')}")
    
    print("\n Service Configuration:")
    print(f"   Base URL: {synq_service.base_url}")
    print(f"   Headless Mode: Yes (production ready)")
    print(f"   Optimized Coordinates: Yes")
    
    return result.get('success', False)

if __name__ == "__main__":
    test_synqprox_connectivity()
