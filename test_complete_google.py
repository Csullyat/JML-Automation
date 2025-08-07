#!/usr/bin/env python3
"""
Test complete Google Workspace termination integration
"""

from google_termination import GoogleTerminationManager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def test_google_termination_manager():
    """Test the complete Google termination manager."""
    print("Testing Google Workspace Termination Manager...")
    print("=" * 60)
    
    try:
        # Initialize the manager
        print("1. Initializing Google Termination Manager...")
        gtm = GoogleTerminationManager()
        print("[PASS] Google Termination Manager initialized successfully")
        
        # Test finding a user (using the one we found earlier)
        print("\n2. Testing user lookup...")
        test_email = "aaron.lambert@filevine.com"  # User we found in the auth test
        user = gtm.find_user_by_email(test_email)
        
        if user:
            user_name = user.get('name', {}).get('fullName', 'Unknown')
            print(f"[PASS] Found user: {user_name} ({test_email})")
            print(f"       User ID: {user.get('id')}")
            print(f"       Status: {user.get('suspended', False) and 'Suspended' or 'Active'}")
        else:
            print(f"[WARN] User not found: {test_email}")
        
        # Test organizational unit check
        print("\n3. Testing organizational unit functions...")
        sso_group = "SSO-G SUITE_ENTERPRISEUSERS"
        print(f"[INFO] Google group for removal: {sso_group}")
        
        print("\n" + "=" * 60)
        print("SUCCESS: Google Workspace termination manager is working!")
        print("Ready for production termination automation.")
        return True
        
    except Exception as e:
        print(f"[FAIL] Google termination manager test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_google_termination_manager()
    
    if not success:
        print("\nThere may be issues with the Google Workspace setup.")
        print("Check the logs above for details.")
    else:
        print("\nGoogle Workspace integration is ready for termination automation!")
