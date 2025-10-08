"""
Systematic Adobe API payload testing based on latest documentation
Following suggestions to resolve "Expected a valid JSON payload" error
"""

import requests
import json
import logging
from jml_automation.config import Config

def test_adobe_payload_variations():
    """Test various Adobe API payload formats systematically."""
    print("=" * 80)
    print("SYSTEMATIC ADOBE API PAYLOAD TESTING")
    print("Following latest Adobe documentation and best practices")
    print("=" * 80)
    
    # Get credentials and token
    config = Config()
    creds = config.get_adobe_credentials_dict()
    
    client_id = creds.get('client_id')
    client_secret = creds.get('client_secret')
    org_id = creds.get('org_id')
    
    # Get OAuth token
    token_url = "https://ims-na1.adobelogin.com/ims/token/v3"
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'ent_user_sdk,openid,AdobeID'
    }
    
    token_response = requests.post(token_url, data=token_data, timeout=30)
    if token_response.status_code != 200:
        print(f" Token failed: {token_response.status_code}")
        return
    
    token = token_response.json().get('access_token')
    print(f" OAuth token obtained successfully")
    
    # Correct endpoint URL (from our testing)
    action_url = f"https://usermanagement.adobe.io/v2/usermanagement/action/{org_id}"
    
    # Test 1: Verify Content-Type header variations
    print(f"\n1. Testing Content-Type header variations...")
    
    base_headers = {
        'Authorization': f'Bearer {token}',
        'X-Api-Key': client_id,
        'X-Gw-Ims-Org-Id': org_id,
        'Accept': 'application/json'
    }
    
    content_type_variants = [
        'application/json',
        'application/json; charset=utf-8',
        'application/json;charset=utf-8'
    ]
    
    # Minimal payload for testing
    minimal_payload = {
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
    
    for i, content_type in enumerate(content_type_variants, 1):
        headers = base_headers.copy()
        headers['Content-Type'] = content_type
        
        print(f"  {i}. Content-Type: {content_type}")
        
        try:
            response = requests.post(
                action_url,
                headers=headers,
                json=minimal_payload,
                timeout=15
            )
            
            if response.status_code == 200:
                print(f"     SUCCESS! User deletion worked!")
                print(f"    Response: {response.text}")
                return True
            elif response.status_code == 400:
                error_text = response.text[:100].replace('\n', ' ')
                print(f"     400: {error_text}...")
            else:
                print(f"     {response.status_code}: {response.text[:50]}...")
                
        except Exception as e:
            print(f"     Error: {str(e)[:50]}...")
    
    # Test 2: Payload structure variations
    print(f"\n2. Testing payload structure variations...")
    
    headers = base_headers.copy()
    headers['Content-Type'] = 'application/json'
    
    payload_variants = [
        # Variant 1: Basic structure (current)
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
        
        # Variant 2: With user type field
        {
            "do": [
                {
                    "removeFromOrg": {
                        "user": {
                            "email": "jordanrosier@filevine.com",
                            "type": "user"
                        }
                    }
                }
            ]
        },
        
        # Variant 3: With requestID
        {
            "requestID": "jml-delete-test-001",
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
        
        # Variant 4: With domain field
        {
            "do": [
                {
                    "removeFromOrg": {
                        "user": {
                            "email": "jordanrosier@filevine.com",
                            "domain": "filevine.com"
                        }
                    }
                }
            ]
        },
        
        # Variant 5: Different action structure
        {
            "do": [
                {
                    "user": {
                        "email": "jordanrosier@filevine.com"
                    },
                    "do": "removeFromOrg"
                }
            ]
        },
        
        # Variant 6: With username field (email as username)
        {
            "do": [
                {
                    "removeFromOrg": {
                        "user": {
                            "email": "jordanrosier@filevine.com",
                            "username": "jordanrosier@filevine.com"
                        }
                    }
                }
            ]
        }
    ]
    
    for i, payload in enumerate(payload_variants, 1):
        print(f"  {i}. Testing payload variant {i}:")
        payload_str = str(payload)[:100] + "..." if len(str(payload)) > 100 else str(payload)
        print(f"     {payload_str}")
        
        try:
            response = requests.post(
                action_url,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                print(f"     SUCCESS! Payload variant {i} worked!")
                print(f"    Response: {response.text}")
                return True
            elif response.status_code == 400:
                error_text = response.text[:100].replace('\n', ' ')
                print(f"     400: {error_text}...")
            else:
                print(f"     {response.status_code}: {response.text[:50]}...")
                
        except Exception as e:
            print(f"     Error: {str(e)[:50]}...")
    
    # Test 3: Raw requests with different JSON serialization
    print(f"\n3. Testing raw JSON serialization...")
    
    import json
    
    test_payload = {
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
    
    json_variants = [
        json.dumps(test_payload),  # Default
        json.dumps(test_payload, separators=(',', ':')),  # Compact
        json.dumps(test_payload, indent=None),  # No indent
    ]
    
    for i, json_str in enumerate(json_variants, 1):
        print(f"  {i}. JSON serialization variant {i}")
        
        try:
            response = requests.post(
                action_url,
                headers=headers,
                data=json_str,  # Use data instead of json
                timeout=15
            )
            
            if response.status_code == 200:
                print(f"     SUCCESS! JSON variant {i} worked!")
                print(f"    Response: {response.text}")
                return True
            elif response.status_code == 400:
                error_text = response.text[:100].replace('\n', ' ')
                print(f"     400: {error_text}...")
            else:
                print(f"     {response.status_code}: {response.text[:50]}...")
                
        except Exception as e:
            print(f"     Error: {str(e)[:50]}...")
    
    print(f"\n All payload variations failed. This suggests:")
    print(f"   1. Adobe Developer Console permissions may be insufficient")
    print(f"   2. API endpoint or authentication method may have changed")
    print(f"   3. Organization-specific configuration may be required")
    print(f"   4. Adobe support consultation may be needed")
    
    return False

if __name__ == "__main__":
    print("WARNING: This will test various payload formats with jordanrosier@filevine.com")
    print("If any succeed, the user will be deleted from Adobe!")
    print("Press Ctrl+C to cancel, or wait 3 seconds to continue...")
    
    import time
    for i in range(3, 0, -1):
        print(f"Starting in {i}...")
        time.sleep(1)
    
    success = test_adobe_payload_variations()
    
    if success:
        print(f"\n Adobe deletion test successful!")
    else:
        print(f"\n Next steps:")
        print(f"   • Review Adobe Developer Console project permissions")
        print(f"   • Check latest Adobe User Management API documentation")
        print(f"   • Test with Adobe's official Postman collection")
        print(f"   • Contact Adobe developer support if needed")