"""
Comprehensive debug of Adobe User Management API
"""

import requests
import json
import logging
from jml_automation.config import Config

def debug_adobe_api():
    """Debug all aspects of Adobe API call."""
    print("=" * 80)
    print("COMPREHENSIVE ADOBE API DEBUG")
    print("=" * 80)
    
    # Get credentials
    config = Config()
    creds = config.get_adobe_credentials_dict()
    
    client_id = creds.get('client_id')
    client_secret = creds.get('client_secret')
    org_id = creds.get('org_id')
    
    print(f"Client ID: {client_id[:20]}...")
    print(f"Org ID: {org_id}")
    
    # Get token
    print("\n1. Getting OAuth Token...")
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
        return
    
    token = token_response.json().get('access_token')
    print(f" Token obtained: {token[:20]}...")
    
    # Test different header combinations
    headers_variants = [
        {
            'Authorization': f'Bearer {token}',
            'X-Api-Key': client_id,
            'X-Gw-Ims-Org-Id': org_id,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        {
            'Authorization': f'Bearer {token}',
            'X-Api-Key': client_id,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        {
            'Authorization': f'Bearer {token}',
            'X-Gw-Ims-Org-Id': org_id,
            'Content-Type': 'application/json'
        }
    ]
    
    # Test different URL formats
    url_variants = [
        f"https://usermanagement.adobe.io/v2/usermanagement/action/{org_id}",
        f"https://usermanagement.adobe.io/v2/usermanagement/organizations/{org_id}/action",
        f"https://usermanagement.adobe.io/v1/usermanagement/action/{org_id}"
    ]
    
    # Test different payload formats
    payload_variants = [
        {
            "do": [
                {
                    "removeFromOrg": {
                        "user": {
                            "email": "jordanrosier@filevine.com"
                        }
                    }
                }
            ]
        },
        {
            "do": [
                {
                    "removeFromOrg": {
                        "user": "jordanrosier@filevine.com"
                    }
                }
            ]
        },
        {
            "requestID": "test-123",
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
    ]
    
    print(f"\n2. Testing {len(url_variants)} URLs × {len(headers_variants)} headers × {len(payload_variants)} payloads...")
    
    for url_idx, url in enumerate(url_variants, 1):
        print(f"\nURL {url_idx}: {url}")
        
        for header_idx, headers in enumerate(headers_variants, 1):
            for payload_idx, payload in enumerate(payload_variants, 1):
                print(f"  Test {header_idx}.{payload_idx}: ", end="")
                
                try:
                    response = requests.post(
                        url,
                        headers=headers,
                        json=payload,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        print(f" SUCCESS! Status: {response.status_code}")
                        print(f"    Response: {response.text[:100]}")
                        return True
                    elif response.status_code == 400:
                        error_msg = response.text[:50].replace('\n', ' ')
                        print(f" 400 - {error_msg}...")
                    elif response.status_code == 404:
                        print(" 404 - Not Found")
                    elif response.status_code == 403:
                        print(" 403 - Forbidden")
                    else:
                        print(f" {response.status_code}")
                        
                except Exception as e:
                    print(f" Error: {str(e)[:30]}...")
    
    print(f"\n3. None of the combinations worked. Let's check user lookup to confirm API access...")
    
    # Test user lookup (which we know works)
    lookup_url = f"https://usermanagement.adobe.io/v2/usermanagement/organizations/{org_id}/users/jordanrosier@filevine.com"
    lookup_headers = headers_variants[0]  # Use the full headers
    
    lookup_response = requests.get(lookup_url, headers=lookup_headers, timeout=30)
    print(f"User lookup status: {lookup_response.status_code}")
    
    if lookup_response.status_code == 200:
        user_data = lookup_response.json()
        user_info = user_data.get('user', {})
        print(f"User found: {user_info.get('email')} (Status: {user_info.get('status')})")
        print(f"Admin roles: {user_info.get('adminRoles', [])}")
        
        # Check if user has admin roles that might prevent deletion
        admin_roles = user_info.get('adminRoles', [])
        if admin_roles:
            print(f"  User has admin roles: {admin_roles}")
            print("   This might prevent normal deletion!")
    
    return False

if __name__ == "__main__":
    debug_adobe_api()