# check_okta_users.py - Check what users exist and their field structure

import logging
from config import get_okta_token, get_okta_domain
import requests
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_okta_users():
    """Check what users exist in Okta and their field structure."""
    
    okta_token = get_okta_token()
    okta_domain = get_okta_domain()
    
    headers = {
        'Authorization': f'SSWS {okta_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        # Get first 10 users to see structure
        logger.info("Fetching sample users from Okta...")
        
        response = requests.get(
            f"https://{okta_domain}/api/v1/users",
            headers=headers,
            params={'limit': 10},
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch users: {response.status_code} - {response.text}")
            return
        
        users = response.json()
        
        logger.info(f"Found {len(users)} sample users:")
        
        for i, user in enumerate(users):
            profile = user.get('profile', {})
            print(f"\nUser {i+1}:")
            print(f"  ID: {user.get('id')}")
            print(f"  Email: {profile.get('email', 'N/A')}")
            print(f"  Name: {profile.get('firstName', '')} {profile.get('lastName', '')}")
            print(f"  Status: {user.get('status', 'N/A')}")
            
            # Check for employee number fields
            employee_fields = {}
            for key, value in profile.items():
                if 'employee' in key.lower() or 'id' in key.lower():
                    employee_fields[key] = value
            
            if employee_fields:
                print(f"  Employee fields: {employee_fields}")
            else:
                print("  No employee ID fields found")
        
        # Also try searching for any user with "Valerie" or "Baird"
        print("\n" + "="*50)
        print("Searching for any Valerie or Baird...")
        
        for search_term in ["Valerie", "Baird"]:
            logger.info(f"Searching for '{search_term}'...")
            
            response = requests.get(
                f"https://{okta_domain}/api/v1/users",
                headers=headers,
                params={'q': search_term, 'limit': 5},
                timeout=30
            )
            
            if response.status_code == 200:
                search_users = response.json()
                if search_users:
                    print(f"\nFound {len(search_users)} users matching '{search_term}':")
                    for user in search_users:
                        profile = user.get('profile', {})
                        print(f"  {profile.get('email', 'N/A')} - {profile.get('firstName', '')} {profile.get('lastName', '')} - Status: {user.get('status', 'N/A')}")
                else:
                    print(f"No users found matching '{search_term}'")
        
    except Exception as e:
        logger.error(f"Exception checking users: {e}")

if __name__ == "__main__":
    check_okta_users()
