#!/usr/bin/env python3
"""
Test script to find the correct Okta profile field names for employee lookup.
"""

import logging
import requests
from config import get_okta_token, get_okta_domain

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_okta_search_variations():
    """Test different variations of employee search in Okta."""
    print("=" * 80)
    print("TESTING OKTA SEARCH FIELD VARIATIONS")
    print("=" * 80)
    
    okta_token = get_okta_token()
    okta_domain = get_okta_domain()
    
    headers = {
        'Authorization': f'SSWS {okta_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    employee_id = "13685751"  # Test with one of our employee IDs
    
    # Try different field variations that might contain employee IDs
    field_variations = [
        'profile.employeeNumber',
        'profile.employeeId', 
        'profile.employee_number',
        'profile.employee_id',
        'profile.empId',
        'profile.empNumber',
        'profile.costCenter',
        'profile.organization',
        'profile.department',
        'profile.managerId'
    ]
    
    print(f"Testing employee ID: {employee_id}\n")
    
    for field in field_variations:
        print(f"Testing field: {field}")
        
        try:
            # Test the search query
            filter_query = f'{field} eq "{employee_id}"'
            
            response = requests.get(
                f"https://{okta_domain}/api/v1/users",
                headers=headers,
                params={'filter': filter_query, 'limit': 1},
                timeout=30
            )
            
            if response.status_code == 200:
                users = response.json()
                if users:
                    user = users[0]
                    print(f"  [SUCCESS] Found user with {field}")
                    print(f"    Name: {user['profile'].get('displayName', 'Unknown')}")
                    print(f"    Email: {user['profile'].get('email', 'Unknown')}")
                    print(f"    Field value: {user['profile'].get(field.split('.')[-1], 'Not found')}")
                    return field  # Return the working field
                else:
                    print(f"  [NO RESULTS] Query worked but no users found")
            elif response.status_code == 400:
                print(f"  [INVALID FIELD] Field doesn't exist or query malformed")
            else:
                print(f"  [ERROR] HTTP {response.status_code}")
                
        except Exception as e:
            print(f"  [EXCEPTION] {e}")
        
        print()
    
    print("No working field found. Let's try a different approach...")
    return None

def get_sample_user_profile():
    """Get a sample user to see what profile fields are available."""
    print("=" * 80)
    print("EXAMINING SAMPLE USER PROFILE FIELDS")
    print("=" * 80)
    
    okta_token = get_okta_token()
    okta_domain = get_okta_domain()
    
    headers = {
        'Authorization': f'SSWS {okta_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        # Get a few users to examine their profiles
        response = requests.get(
            f"https://{okta_domain}/api/v1/users",
            headers=headers,
            params={'limit': 3},
            timeout=30
        )
        
        if response.status_code == 200:
            users = response.json()
            
            if users:
                print(f"Found {len(users)} sample users. Examining profiles...\n")
                
                for i, user in enumerate(users, 1):
                    profile = user.get('profile', {})
                    print(f"USER {i}:")
                    print(f"  Name: {profile.get('displayName', 'Unknown')}")
                    print(f"  Email: {profile.get('email', 'Unknown')}")
                    print(f"  Login: {profile.get('login', 'Unknown')}")
                    print(f"  Profile fields:")
                    
                    # Show all profile fields that might contain employee data
                    employee_related_fields = []
                    for key, value in profile.items():
                        if any(word in key.lower() for word in ['employee', 'emp', 'id', 'number', 'cost', 'manager']):
                            employee_related_fields.append(f"    {key}: {value}")
                        elif key not in ['email', 'login', 'firstName', 'lastName', 'displayName']:
                            employee_related_fields.append(f"    {key}: {value}")
                    
                    if employee_related_fields:
                        print("\n".join(employee_related_fields))
                    else:
                        print("    No employee-related fields found")
                    
                    print()
            else:
                print("No users returned")
        else:
            print(f"Error getting users: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Main test function."""
    print("OKTA FIELD NAME DISCOVERY TEST")
    print("Finding the correct field name for employee ID lookups")
    print()
    
    # First, try variations of employee field names
    working_field = test_okta_search_variations()
    
    if not working_field:
        # If no field worked, examine actual user profiles
        get_sample_user_profile()
        
        print("\n" + "=" * 80)
        print("CONCLUSION")
        print("=" * 80)
        print("Based on the sample user profiles above:")
        print("1. Look for fields that might contain employee IDs")
        print("2. The field name might be different than 'employeeNumber'")
        print("3. Employee IDs might be stored in a custom field")
        print("4. Or the integration might work differently")
    else:
        print(f"SUCCESS! Use field: {working_field}")

if __name__ == "__main__":
    main()