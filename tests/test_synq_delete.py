#!/usr/bin/env python3
"""
Test script for SYNQ Prox user deletion.
Tests removing access for codyatkinson@filevine.com.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from jml_automation.services.synqprox import SynqProxService
import logging

# Set up logging to see what happens
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)

def test_synq_delete():
    """Test SYNQ Prox user deletion."""
    print("=== Testing SYNQ Prox User Deletion ===")
    
    # Initialize the service
    service = SynqProxService()
    
    # Test email
    test_email = "codyatkinson@filevine.com"
    
    print(f"Testing deletion of user: {test_email}")
    
    try:
        # Test the delete function
        result = service.delete_user(test_email)
        
        if result:
            print(f"✅ Successfully deleted user: {test_email}")
        else:
            print(f"❌ Failed to delete user: {test_email}")
            
    except Exception as e:
        print(f"❌ Error during deletion test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_synq_delete()
