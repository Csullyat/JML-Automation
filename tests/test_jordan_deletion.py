"""
Test Adobe user deletion for jordanrosier@filevine.com using service account
"""

import logging
from jml_automation.services.adobe import AdobeService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_jordan_deletion():
    """Test Adobe user deletion for jordanrosier@filevine.com in production mode."""
    email = "jordanrosier@filevine.com"
    
    print(f"PRODUCTION TEST: Attempting to delete {email} from Adobe")
    print("This will free up the license if successful")
    print("=" * 60)
    
    try:
        # Initialize Adobe service in production mode
        adobe = AdobeService(dry_run=False)
        
        # Test 1: Connectivity
        print("\n1. Testing Adobe connectivity...")
        if not adobe.test_connection():
            print("Adobe connectivity failed")
            return False
        print("Adobe connectivity successful")
        
        # Test 2: Check if user exists in Adobe
        print(f"\n2. Looking up user {email} in Adobe...")
        user_id = adobe.find_user_by_email(email)
        if not user_id:
            print(f"   User {email} not found in Adobe - nothing to delete")
            return True
        print(f"   User found: {email}")
        
        # Test 3: Check Okta groups
        print(f"\n3. Checking Okta groups for {email}...")
        groups = adobe.check_okta_groups(email)
        print(f"   Groups: {groups}")
        
        if not groups.get("SSO-Adobe", False):
            print(f"   User {email} not in SSO-Adobe group - no action needed")
            return True
        
        # Test 4: Attempt user deletion
        print(f"\n4. Attempting to delete {email} from Adobe...")
        success = adobe.terminate_user(email)
        
        if success:
            print(f"SUCCESS: {email} deleted from Adobe and removed from SSO-Adobe group")
            print("License should now be freed up!")
            return True
        else:
            print(f"FAILED: Could not delete {email} from Adobe")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("WARNING: This will actually attempt to delete jordanrosier@filevine.com from Adobe!")
    print("This should free up the license.")
    print("Press Ctrl+C to cancel, or wait 5 seconds to continue...")
    
    import time
    for i in range(5, 0, -1):
        print(f"Starting in {i}...")
        time.sleep(1)
    
    success = test_jordan_deletion()
    print("\n" + "=" * 60)
    if success:
        print("Adobe deletion test completed successfully!")
    else:
        print("Adobe deletion test failed")