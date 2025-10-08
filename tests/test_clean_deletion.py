"""
Single clean Adobe deletion attempt after rate limit reset
"""

import requests
import json
import time
import logging
from jml_automation.config import Config

def single_clean_deletion_attempt():
    """Make a single, clean deletion attempt after waiting for rate limit reset."""
    print("=" * 80)
    print("SINGLE CLEAN ADOBE DELETION ATTEMPT")
    print("Waiting for rate limit to reset, then making one clean attempt")
    print("=" * 80)
    
    # Wait for rate limit to reset (Adobe typically uses 1-minute windows)
    print("Waiting 90 seconds for Adobe API rate limit to reset...")
    for i in range(90, 0, -10):
        print(f"  {i} seconds remaining...")
        time.sleep(10)
    
    print(" Rate limit wait complete. Making clean deletion attempt...")
    
    # Get credentials and token
    config = Config()
    creds = config.get_adobe_credentials_dict()
    
    client_id = creds.get('client_id')
    client_secret = creds.get('client_secret')
    org_id = creds.get('org_id')
    
    # Get fresh OAuth token
    print("\n1. Getting fresh OAuth token...")
    token_url = "https://ims-na1.adobelogin.com/ims/token/v3"
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'ent_user_sdk,openid,AdobeID'
    }
    
    token_response = requests.post(token_url, data=token_data, timeout=30)
    if token_response.status_code != 200:
        print(f" Token failed: {token_response.status_code} - {token_response.text}")
        return False
    
    token = token_response.json().get('access_token')
    print(f" Fresh OAuth token obtained")
    
    # Use the correct endpoint and headers
    action_url = f"https://usermanagement.adobe.io/v2/usermanagement/action/{org_id}"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'X-Api-Key': client_id,
        'X-Gw-Ims-Org-Id': org_id,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Use the corrected payload format
    payload = {
        "do": [
            {
                "removeFromOrg": {
                    "user": {
                        "email": "jordanrosier@filevine.com"
                    }
                }
            }
        ]
    }
    
    print(f"\n2. Making deletion request...")
    print(f"   URL: {action_url}")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            action_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"\n3. Response received:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        print(f"   Body: {response.text}")
        
        if response.status_code == 200:
            print(f"\n SUCCESS! Jordan has been deleted from Adobe!")
            print(f"License should now be freed up!")
            return True
        elif response.status_code == 400:
            print(f"\n Still getting 400 error. This suggests:")
            print(f"   • Adobe Developer Console permissions may be insufficient")
            print(f"   • Specific API scope or permission missing")
            print(f"   • Organization configuration issue")
            return False
        elif response.status_code == 429:
            print(f"\n Still rate limited. Adobe may have longer rate limit windows.")
            return False
        else:
            print(f"\n Unexpected response code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n Request failed: {e}")
        return False

if __name__ == "__main__":
    print("This will wait 90 seconds, then make ONE clean deletion attempt.")
    print("If successful, jordanrosier@filevine.com will be deleted from Adobe!")
    
    response = input("Continue? (y/N): ")
    if response.lower() != 'y':
        print("Cancelled.")
        exit()
    
    success = single_clean_deletion_attempt()
    
    if success:
        print(f"\n Adobe deletion successful! License freed up!")
    else:
        print(f"\n If this still fails, next steps:")
        print(f"   1. Check Adobe Developer Console for missing permissions")
        print(f"   2. Verify User Management API scope requirements") 
        print(f"   3. Contact Adobe developer support with error details")
        print(f"   4. Test with Adobe's official Postman collection")