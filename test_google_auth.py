#!/usr/bin/env python3
"""
Test Google Workspace authentication with service account
"""

import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import get_google_service_account_key

def test_google_auth():
    """Test Google Workspace authentication"""
    print("Testing Google Workspace Authentication...")
    print("=" * 50)
    
    try:
        # Get service account key
        print("1. Retrieving service account key from 1Password...")
        service_account_key = get_google_service_account_key()
        
        if not service_account_key:
            print("[FAIL] No service account key found in 1Password")
            return False
            
        print("[PASS] Service account key retrieved successfully")
        
        # Validate the credentials dict
        print("2. Validating service account credentials...")
        try:
            key_data = service_account_key  # Already a dict from config
            print(f"[PASS] Service account email: {key_data.get('client_email', 'Unknown')}")
            print(f"[PASS] Project ID: {key_data.get('project_id', 'Unknown')}")
        except Exception as e:
            print(f"[FAIL] Failed to validate service account data: {e}")
            return False
        
        # Create credentials
        print("3. Creating Google API credentials...")
        credentials = service_account.Credentials.from_service_account_info(
            key_data, 
            scopes=[
                'https://www.googleapis.com/auth/admin.directory.user',
                'https://www.googleapis.com/auth/admin.datatransfer'
            ]
        )
        
        # Delegate to admin user (required for admin SDK)
        # Try multiple possible admin emails
        possible_admins = [
            "codyatkinson@filevine.com",
            "admin@filevine.com",
            "administrator@filevine.com", 
            "it@filevine.com"
        ]
        
        success = False
        for admin_email in possible_admins:
            try:
                print(f"   Trying admin email: {admin_email}")
                delegated_credentials = credentials.with_subject(admin_email)
                
                # Test Directory API connection
                print("4. Testing Google Admin Directory API connection...")
                service = build('admin', 'directory_v1', credentials=delegated_credentials)
                
                # Try to list users (just to test the connection)
                print("5. Testing API call (listing first user)...")
                result = service.users().list(domain='filevine.com', maxResults=1).execute()
                users = result.get('users', [])
                
                if users:
                    user = users[0]
                    print(f"[PASS] API call successful with {admin_email}! Found user: {user.get('primaryEmail', 'Unknown')}")
                    success = True
                    break
                else:
                    print(f"[PASS] API call successful with {admin_email} but no users returned")
                    success = True
                    break
                    
            except Exception as e:
                print(f"   Failed with {admin_email}: {e}")
                continue
        
        if not success:
            print("[FAIL] Could not authenticate with any admin email")
            print("Make sure domain-wide delegation is configured for the service account")
            return False
            
        return True
            
    except Exception as e:
        print(f"[FAIL] Authentication test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_google_auth()
    
    if success:
        print("\n" + "=" * 50)
        print("SUCCESS: Google Workspace authentication is working!")
        print("The termination automation can now use Google APIs.")
    else:
        print("\n" + "=" * 50)
        print("FAILED: Google Workspace authentication needs attention.")
        print("Check the service account setup and domain-wide delegation.")
