"""
Direct test of Adobe user deletion for codyatkinson@filevine.com
"""

import logging
from jml_automation.services.adobe import AdobeService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_cody_deletion():
    """Test Adobe user deletion for codyatkinson@filevine.com in production mode."""
    email = "codyatkinson@filevine.com"
    
    print(f"PRODUCTION TEST: Attempting to delete {email} from Adobe")
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
        
        # Test 2: Check Okta groups
        print(f"\n2. Checking Okta groups for {email}...")
        groups = adobe.check_okta_groups(email)
        print(f"   Groups: {groups}")
        
        if not groups.get("SSO-Adobe", False):
            print(f"   User {email} not in SSO-Adobe group - no action needed")
            return True
        
        # Test 3: Attempt user deletion
        print(f"\n3. Attempting to delete {email} from Adobe...")
        success = adobe.terminate_user(email)
        
        if success:
            print(f"SUCCESS: {email} deleted from Adobe and removed from SSO-Adobe group")
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
    print("WARNING: This will actually attempt to delete codyatkinson@filevine.com from Adobe!")
    print("Press Ctrl+C to cancel, or wait 5 seconds to continue...")
    
    import time
    for i in range(5, 0, -1):
        print(f"Starting in {i}...")
        time.sleep(1)
    
    success = test_cody_deletion()
    print("\n" + "=" * 60)
    if success:
        print("Adobe deletion test completed successfully!")
    else:
        print("Adobe deletion test failed")