"""
Test different Adobe OAuth scopes to find the correct one
"""

import requests
import logging
from jml_automation.config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_scope(scope):
    """Test a specific OAuth scope."""
    print(f"\nTesting scope: {scope}")
    print("-" * 40)
    
    # Get credentials
    config = Config()
    creds = config.get_adobe_credentials_dict()
    client_id = creds.get('client_id')
    client_secret = creds.get('client_secret')
    
    if not client_id or not client_secret:
        print("Missing OAuth credentials")
        return False
        
    try:
        token_url = "https://ims-na1.adobelogin.com/ims/token/v3"
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': scope
        }
        
        response = requests.post(token_url, data=data, timeout=30)
        
        if response.status_code == 200:
            token_data = response.json()
            print(f"SUCCESS: Scope '{scope}' works!")
            print(f"Returned scope: {token_data.get('scope', 'unknown')}")
            print(f"Token type: {token_data.get('token_type', 'unknown')}")
            return True
        else:
            print(f"FAILED: Status {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    """Test various Adobe OAuth scopes."""
    print("Testing Adobe OAuth scopes...")
    print("=" * 60)
    
    # Common Adobe scopes to test
    scopes_to_test = [
        # User Management specific scopes
        'ent_user_sdk',
        'user_mgmt_sdk',
        'usermanagement_sdk',
        'usermanagement',
        
        # Generic Adobe scopes
        'openid',
        'AdobeID',
        'read_organizations',
        'additional_info.projectedProductContext',
        
        # Creative SDK scopes
        'creative_sdk',
        
        # Multiple scopes
        'openid,AdobeID',
        'openid,AdobeID,read_organizations',
        'ent_user_sdk,openid,AdobeID',
        
        # Empty scope (sometimes works)
        ''
    ]
    
    successful_scopes = []
    
    for scope in scopes_to_test:
        if test_scope(scope):
            successful_scopes.append(scope)
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    if successful_scopes:
        print(f"Working scopes: {successful_scopes}")
    else:
        print("No working scopes found")

if __name__ == "__main__":
    main()