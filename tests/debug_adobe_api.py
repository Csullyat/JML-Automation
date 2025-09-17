"""
Debug Adobe User Management API calls
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

def test_adobe_api():
    """Test Adobe API endpoints."""
    print("Testing Adobe User Management API...")
    print("=" * 60)
    
    # Get credentials
    config = Config()
    creds = config.get_adobe_credentials_dict()
    
    client_id = creds.get('client_id')
    client_secret = creds.get('client_secret')
    org_id = creds.get('org_id')
    
    if not all([client_id, client_secret, org_id]):
        print("Missing OAuth credentials")
        return
        
    # Get access token
    print("1. Getting access token...")
    token_url = "https://ims-na1.adobelogin.com/ims/token/v3"
    
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'ent_user_sdk,openid,AdobeID'
    }
    
    token_response = requests.post(token_url, data=token_data, timeout=30)
    
    if token_response.status_code != 200:
        print(f"Failed to get token: {token_response.status_code} - {token_response.text}")
        return
        
    token = token_response.json().get('access_token')
    print(f"Got token: {token[:20]}...")
    
    # Set up headers
    headers = {
        'Authorization': f'Bearer {token}',
        'X-Api-Key': client_id,
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    base_url = f"https://usermanagement.adobe.io/v2/usermanagement/organizations/{org_id}"
    
    # Test 1: Get user info
    print(f"\n2. Testing user lookup for codyatkinson@filevine.com...")
    user_url = f"{base_url}/users/codyatkinson@filevine.com"
    print(f"URL: {user_url}")
    
    user_response = requests.get(user_url, headers=headers, timeout=30)
    print(f"Status: {user_response.status_code}")
    if user_response.status_code == 200:
        user_data = user_response.json()
        print(f"User data: {json.dumps(user_data, indent=2)}")
    else:
        print(f"Error: {user_response.text}")
    
    # Test 2: Test action endpoint structure
    print(f"\n3. Testing action endpoint...")
    action_url = f"{base_url}/action"
    print(f"URL: {action_url}")
    
    # Test with minimal valid payload first
    test_payload = {
        "do": [
            {
                "removeFromOrg": {
                    "user": "codyatkinson@filevine.com"
                }
            }
        ]
    }
    
    print(f"Payload: {json.dumps(test_payload, indent=2)}")
    
    # Make the request
    action_response = requests.post(
        action_url,
        headers=headers,
        json=test_payload,
        timeout=30
    )
    
    print(f"Status: {action_response.status_code}")
    print(f"Response: {action_response.text}")
    
    # Test 3: Try different payload formats
    if action_response.status_code == 400:
        print(f"\n4. Testing alternative payload formats...")
        
        # Try with user object instead of email string
        alt_payload = {
            "do": [
                {
                    "removeFromOrg": {
                        "user": {
                            "email": "codyatkinson@filevine.com"
                        }
                    }
                }
            ]
        }
        
        print(f"Alternative payload: {json.dumps(alt_payload, indent=2)}")
        
        alt_response = requests.post(
            action_url,
            headers=headers,
            json=alt_payload,
            timeout=30
        )
        
        print(f"Alt Status: {alt_response.status_code}")
        print(f"Alt Response: {alt_response.text}")

if __name__ == "__main__":
    test_adobe_api()