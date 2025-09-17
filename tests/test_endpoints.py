"""
Test different Adobe User Management API endpoint formats
"""

import requests
import json
import logging
from jml_automation.config import Config

def test_endpoints():
    """Test different endpoint formats."""
    print("Testing Adobe User Management API endpoint variations...")
    print("=" * 70)
    
    # Get credentials and token (abbreviated)
    config = Config()
    creds = config.get_adobe_credentials_dict()
    
    client_id = creds.get('client_id')
    client_secret = creds.get('client_secret')
    org_id = creds.get('org_id')
    
    # Get token
    token_url = "https://ims-na1.adobelogin.com/ims/token/v3"
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'ent_user_sdk,openid,AdobeID'
    }
    
    token_response = requests.post(token_url, data=token_data, timeout=30)
    token = token_response.json().get('access_token')
    
    headers = {
        'Authorization': f'Bearer {token}',
        'X-Api-Key': client_id,
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    # Test different base URLs and endpoint formats
    endpoints_to_test = [
        # Different API versions and formats
        f"https://usermanagement.adobe.io/v2/usermanagement/action/{org_id}",
        f"https://usermanagement.adobe.io/v2/usermanagement/organizations/{org_id}/action",
        f"https://usermanagement.adobe.io/action/{org_id}",
        f"https://usermanagement.adobe.io/v2/action/{org_id}",
        f"https://usermanagement.adobe.io/v1/usermanagement/action/{org_id}",
        
        # Alternative domain formats
        f"https://usermanagement-stage.adobe.io/v2/usermanagement/organizations/{org_id}/action",
        f"https://user-management.adobe.io/v2/usermanagement/organizations/{org_id}/action",
        
        # Different organization ID formats (without @AdobeOrg suffix)
        f"https://usermanagement.adobe.io/v2/usermanagement/organizations/{org_id.replace('@AdobeOrg', '')}/action",
    ]
    
    test_payload = {
        "do": [
            {
                "removeFromOrg": {
                    "user": "codyatkinson@filevine.com"
                }
            }
        ]
    }
    
    for i, endpoint in enumerate(endpoints_to_test, 1):
        print(f"\n{i}. Testing: {endpoint}")
        
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=test_payload,
                timeout=30
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code != 404:
                print(f"   Response: {response.text[:200]}...")
                if response.status_code in [200, 201, 400]:
                    print(f"   ^^ POTENTIAL WORKING ENDPOINT! ^^")
            else:
                print(f"   404 - Not Found")
                
        except Exception as e:
            print(f"   Error: {e}")
    
    # Also test if this user can be removed at all (might be protected admin)
    print(f"\n\nUser Analysis:")
    print(f"User ID: 68CC1F5A67D882E40A495CD2@cb297559614713ce495ea9.e")
    print(f"Email: codyatkinson@filevine.com")
    print(f"Status: active")
    print(f"Type: federatedID")
    print(f"Admin Roles: org, support")
    print(f"Groups: {len(['_product_admin_Adobe Captivate', '_product_admin_Acrobat Pro', '_admin_CCMTeamDelegates', '_contract_admin_VIP', '_support_admin'])} groups")
    print(f"\nNOTE: User has 'org' and 'support' admin roles - this might prevent normal deletion!")

if __name__ == "__main__":
    test_endpoints()