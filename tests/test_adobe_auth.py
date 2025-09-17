"""
Test Adobe OAuth S2S authentication in production mode
"""

import logging
from jml_automation.services.adobe import AdobeService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_adobe_production_auth():
    """Test Adobe OAuth S2S authentication in production mode."""
    print("Testing Adobe OAuth S2S authentication (production mode)")
    print("=" * 60)
    
    try:
        # Initialize Adobe service in production mode
        adobe = AdobeService(dry_run=False)
        
        # Test 1: Check credential retrieval
        print("\n1. Testing credential retrieval...")
        creds_ok = adobe._get_credentials()
        if creds_ok:
            print("Adobe OAuth S2S credentials retrieved successfully")
            print(f"   Client ID: {adobe.client_id[:8]}..." if adobe.client_id else "None")
            print(f"   Client Secret: {'[REDACTED]' if adobe.client_secret else 'None'}")
            print(f"   Org ID: {adobe.org_id[:8]}..." if adobe.org_id else "None")
        else:
            print("Failed to retrieve Adobe credentials")
            return False
        
        # Test 2: Test OAuth token generation
        print("\n2. Testing OAuth token generation...")
        access_token = adobe._get_access_token()
        if access_token:
            print("OAuth access token generated successfully")
            print(f"   Token: {access_token[:20]}...")
        else:
            print("Failed to generate OAuth access token")
            return False
        
        # Test 3: Test API connection
        print("\n3. Testing Adobe API connection...")
        connectivity = adobe.test_connection()
        if connectivity:
            print("Adobe API connection successful!")
        else:
            print("Adobe API connection failed")
            return False
        
        return True
            
    except Exception as e:
        print(f"Error during Adobe authentication test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_adobe_production_auth()
    print("\n" + "=" * 60)
    if success:
        print("Adobe OAuth S2S authentication working!")
        print("Ready to test user deletion with codyatkinson@filevine.com")
    else:
        print("Adobe authentication failed - check credentials or API setup")