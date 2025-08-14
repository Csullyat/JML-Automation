#!/usr/bin/env python3
"""
Test script to verify Okta employee ID lookup functionality.
This tests the original intended workflow: Employee ID -> Okta User -> Email
"""

import logging
from datetime import datetime
from config import get_okta_token, get_okta_domain
import requests

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_user_by_employee_id(employee_id: str) -> dict:
    """Find Okta user by employee ID - original functionality."""
    try:
        okta_token = get_okta_token()
        okta_domain = get_okta_domain()
        
        headers = {
            'Authorization': f'SSWS {okta_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Search by employeeNumber field (this is the key!)
        filter_query = f'profile.employeeNumber eq "{employee_id}"'
        
        response = requests.get(
            f"https://{okta_domain}/api/v1/users",
            headers=headers,
            params={'filter': filter_query},
            timeout=30
        )
        
        if response.status_code == 200:
            users = response.json()
            if users:
                user = users[0]  # Return first match
                return {
                    'found': True,
                    'employee_id': employee_id,
                    'okta_user_id': user['id'],
                    'email': user['profile'].get('email', 'No email'),
                    'login': user['profile'].get('login', 'No login'), 
                    'display_name': user['profile'].get('displayName', 'No name'),
                    'employee_number': user['profile'].get('employeeNumber', 'No employee number')
                }
            else:
                return {
                    'found': False,
                    'employee_id': employee_id,
                    'error': 'No users found with this employee ID'
                }
        else:
            logger.error(f"Error searching for employee {employee_id}: {response.status_code}")
            return {
                'found': False,
                'employee_id': employee_id,
                'error': f'API error: {response.status_code}'
            }
            
    except Exception as e:
        logger.error(f"Exception finding employee {employee_id}: {e}")
        return {
            'found': False,
            'employee_id': employee_id,
            'error': str(e)
        }

def test_employee_lookups():
    """Test employee ID lookups with the IDs from our ticket data."""
    print("=" * 80)
    print("TESTING OKTA EMPLOYEE ID LOOKUP FUNCTIONALITY")
    print("=" * 80)
    
    # Test with the employee IDs from the ticket we found
    test_employee_ids = [
        "13685751",  # User from current ticket
        "10493746",  # Manager from current ticket  
        "7467777",   # Manager from other tickets
        "13178254",  # Another user we saw
        "13203385"   # Another user we saw
    ]
    
    print(f"\nTesting {len(test_employee_ids)} employee IDs from ticket data:\n")
    
    results = []
    for employee_id in test_employee_ids:
        print(f"Looking up Employee ID: {employee_id}")
        result = find_user_by_employee_id(employee_id)
        results.append(result)
        
        if result['found']:
            print(f"  [SUCCESS] Found user!")
            print(f"    Email: {result['email']}")
            print(f"    Login: {result['login']}")
            print(f"    Name: {result['display_name']}")
            print(f"    Employee Number in Okta: {result['employee_number']}")
        else:
            print(f"  [NOT FOUND] {result['error']}")
        
        print()
    
    # Summary
    found_count = sum(1 for r in results if r['found'])
    print("=" * 60)
    print("LOOKUP SUMMARY")
    print("=" * 60)
    print(f"Employee IDs tested: {len(test_employee_ids)}")
    print(f"Users found in Okta: {found_count}")
    print(f"Users not found: {len(test_employee_ids) - found_count}")
    
    if found_count > 0:
        print(f"\nSUCCESSFUL LOOKUPS:")
        for result in results:
            if result['found']:
                print(f"  Employee {result['employee_id']} -> {result['email']} ({result['display_name']})")
    
    not_found = [r for r in results if not r['found']]
    if not_found:
        print(f"\nNOT FOUND:")
        for result in not_found:
            print(f"  Employee {result['employee_id']}: {result['error']}")
    
    return results

def main():
    """Main test function."""
    print("OKTA EMPLOYEE ID LOOKUP TEST")
    print("This tests the original intended workflow:")
    print("Employee ID from ticket -> Look up in Okta -> Get actual email")
    print()
    
    results = test_employee_lookups()
    
    # Determine if the original system design would work
    found_any = any(r['found'] for r in results)
    
    if found_any:
        print("\n[SUCCESS] Original design can work!")
        print("The system should:")
        print("1. Extract employee IDs from tickets (we're doing this)")
        print("2. Look up users in Okta by employee ID (this works)")
        print("3. Use the returned email addresses for termination")
    else:
        print("\n[ISSUE] Original design has problems:")
        print("Either the employee IDs aren't in Okta or the field mapping is wrong")
        print("We may need to check:")
        print("- Different Okta profile field names")
        print("- Whether these are test/old employee IDs")
        print("- Okta API permissions")

if __name__ == "__main__":
    main()