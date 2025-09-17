"""
Test alternative Adobe User Management API action formats
"""

import requests
import json
import logging
from jml_automation.config import Config

def test_alternative_actions():
    """Test different action formats for Adobe User Management API."""
    print("=" * 80)
    print("TESTING ALTERNATIVE ADOBE API ACTION FORMATS")
    print("=" * 80)
    
    # Get credentials and token
    config = Config()
    creds = config.get_adobe_credentials_dict()
    
    client_id = creds.get('client_id')
    client_secret = creds.get('client_secret')
    org_id = creds.get('org_id')
    
    # Get fresh token with correct scopes
    token_url = "https://ims-na1.adobelogin.com/ims/token/v3"
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'openid,AdobeID,user_management_sdk'
    }
    
    token_response = requests.post(token_url, data=token_data, timeout=30)
    if token_response.status_code != 200:
        print(f"❌ Token failed: {token_response.status_code}")
        return
    
    token = token_response.json().get('access_token')
    print(f"✅ OAuth token obtained with correct scopes")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'X-Api-Key': client_id,
        'X-Gw-Ims-Org-Id': org_id,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    action_url = f"https://usermanagement.adobe.io/v2/usermanagement/action/{org_id}"
    
    # Test different action formats
    action_variants = [
        # Variant 1: removeFromOrg with requestID
        {
            "requestID": "test-001",
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
        
        # Variant 2: Different action name
        {
            "do": [
                {
                    "deleteUser": {
                        "user": {
                            "email": "jordanrosier@filevine.com"
                        }
                    }
                }
            ]
        },
        
        # Variant 3: remove action
        {
            "do": [
                {
                    "remove": {
                        "user": {
                            "email": "jordanrosier@filevine.com"
                        }
                    }
                }
            ]
        },
        
        # Variant 4: With user ID instead of email (if we can get it)
        {
            "do": [
                {
                    "removeFromOrg": {
                        "user": "jordanrosier@filevine.com"
                    }
                }
            ]
        },
        
        # Variant 5: Simplified structure
        {
            "removeFromOrg": {
                "user": {
                    "email": "jordanrosier@filevine.com"
                }
            }
        }
    ]
    
    for i, payload in enumerate(action_variants, 1):
        print(f"\n{i}. Testing action variant {i}:")
        payload_str = json.dumps(payload, indent=2)[:200] + "..." if len(json.dumps(payload)) > 200 else json.dumps(payload, indent=2)
        print(f"   {payload_str}")
        
        try:
            response = requests.post(
                action_url,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                print(f"   🎉 SUCCESS! Variant {i} worked!")
                print(f"   Response: {response.text}")
                return True
            elif response.status_code == 400:
                error_text = response.text[:100].replace('\n', ' ')
                print(f"   ❌ 400: {error_text}...")
            elif response.status_code == 429:
                print(f"   ⏰ 429: Rate limited")
                break  # Stop testing if rate limited
            else:
                print(f"   ❓ {response.status_code}: {response.text[:50]}...")
                
        except Exception as e:
            print(f"   💥 Error: {str(e)[:50]}...")
    
    print(f"\n📋 All variants failed. This strongly suggests:")
    print(f"   1. Adobe organization may have API restrictions")
    print(f"   2. User may have special status preventing deletion")
    print(f"   3. Additional API permissions may be required beyond User Management")
    print(f"   4. Adobe may require manual approval for user deletions")
    
    return False

if __name__ == "__main__":
    print("Testing alternative Adobe API action formats...")
    print("If any succeed, jordanrosier@filevine.com will be deleted!")
    
    response = input("Continue? (y/N): ")
    if response.lower() != 'y':
        print("Cancelled.")
        exit()
    
    success = test_alternative_actions()
    
    if not success:
        print(f"\n💡 Recommendation: Contact Adobe support with:")
        print(f"   • Organization ID: E0702CB358BDC27A0A495C70@AdobeOrg")
        print(f"   • API endpoint: /v2/usermanagement/action/")
        print(f"   • Error: 'Expected a valid JSON payload'")
        print(f"   • Scopes: openid,AdobeID,user_management_sdk")