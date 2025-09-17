"""
Test correct Adobe action endpoint format based on documentation
"""

import requests
import json
import logging
from jml_automation.config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_correct_endpoint():
    """Test the correct Adobe API endpoint format."""
    print("Testing correct Adobe User Management API action endpoint...")
    print("=" * 70)
    
    # Get credentials
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
        'X-Gw-Ims-Org-Id': org_id,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Try the correct endpoint format based on Adobe documentation
    # The correct format should be: /v2/usermanagement/action/{orgId}
    correct_url = f"https://usermanagement.adobe.io/v2/usermanagement/action/{org_id}"
    
    print(f"Testing URL: {correct_url}")
    
    # Test payload according to Adobe User Management API docs
    test_payload = {
        "do": [
            {
                "removeFromOrg": {
                    "user": "jordanrosier@filevine.com"
                }
            }
        ]
    }
    
    print(f"Payload: {json.dumps(test_payload, indent=2)}")
    print(f"Headers: {json.dumps({k: v for k, v in headers.items() if k != 'Authorization'}, indent=2)}")
    
    try:
        response = requests.post(
            correct_url,
            headers=headers,
            json=test_payload,
            timeout=30
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("\n🎉 SUCCESS! User deletion worked!")
            return True
        elif response.status_code == 400:
            print("\n❌ Still getting 400 error - checking alternative formats...")
            return False
        elif response.status_code == 404:
            print("\n❌ 404 - Endpoint not found")
            return False
        else:
            print(f"\n❓ Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("WARNING: This will attempt to actually delete jordanrosier@filevine.com!")
    print("Press Ctrl+C to cancel, or wait 3 seconds to continue...")
    
    import time
    for i in range(3, 0, -1):
        print(f"Starting in {i}...")
        time.sleep(1)
    
    test_correct_endpoint()