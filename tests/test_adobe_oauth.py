"""
Quick test for Adobe OAuth S2S implementation
"""

import logging
from jml_automation.services.adobe import AdobeService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_adobe_credentials():
    """Test Adobe OAuth S2S credentials and fallback."""
    email = "codyatkinson@filevine.com"
    
    print(f"\nTesting Adobe integration for: {email}")
    print("=" * 60)
    
    try:
        # Initialize Adobe service in dry run mode
        adobe = AdobeService(dry_run=True)
        
        # Test 1: Check credential retrieval
        print("\n1. Testing credential retrieval...")
        creds_ok = adobe._get_credentials()
        if creds_ok:
            print("Adobe credentials retrieved successfully")
            print(f"   OAuth S2S available: {bool(adobe.client_id and adobe.client_secret and adobe.org_id)}")
            print(f"   API key available: {bool(adobe.api_key)}")
        else:
            print("Failed to retrieve Adobe credentials")
            return False
        
        # Test 2: Test connection
        print("\n2. Testing API connection...")
        connectivity = adobe.test_connection()
        if connectivity:
            print("Adobe API connection test passed (dry run)")
        else:
            print("Adobe API connection failed")
            return False
        
        # Test 3: Check Okta groups
        print(f"\n3. Checking Okta group membership for {email}...")
        group_membership = adobe.check_okta_groups(email)
        print(f"   Group membership: {group_membership}")
        
        # Test 4: Full termination workflow (dry run)
        print(f"\n4. Running Adobe termination workflow (DRY RUN)...")
        success = adobe.terminate_user(email)
        
        if success:
            print(f"Adobe test passed for {email}")
            print("   - Workflow completed successfully in dry run mode")
            return True
        else:
            print(f"Adobe test failed for {email}")
            return False
            
    except Exception as e:
        print(f"Error during Adobe test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_adobe_credentials()
    print("\n" + "=" * 60)
    if success:
        print("Adobe integration test completed successfully!")
        print("\nNext steps:")
        print("1. Get OAuth Server-to-Server credentials from Adobe Developer Console")
        print("2. Add client_id, client_secret, and org_id fields to 1Password Adobe API item")
        print("3. Test with production mode")
    else:
        print("Adobe integration test failed - check configuration")