#!/usr/bin/env python3
"""
Test the correct Okta search syntax for employee numbers.
"""

import logging
import requests
from config import get_okta_token, get_okta_domain

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_correct_employee_search():
    """Test the correct employee number search syntax."""
    print("=" * 80)
    print("TESTING CORRECT OKTA EMPLOYEE NUMBER SEARCH")
    print("=" * 80)
    
    okta_token = get_okta_token()
    okta_domain = get_okta_domain()
    
    headers = {
        'Authorization': f'SSWS {okta_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Test with known employee number from sample data
    known_employee_number = "2523"  # From dallasclinger@filevine.com
    
    print(f"Testing with known employee number: {known_employee_number}")
    
    try:
        # Try the correct syntax (without 'profile.' prefix in search)
        search_query = f'employeeNumber eq "{known_employee_number}"'
        
        response = requests.get(
            f"https://{okta_domain}/api/v1/users",
            headers=headers,
            params={'search': search_query},  # Using 'search' instead of 'filter'
            timeout=30
        )
        
        if response.status_code == 200:
            users = response.json()
            if users:
                user = users[0]
                print(f"  [SUCCESS] Found user with search query!")
                print(f"    Name: {user['profile'].get('displayName')}")
                print(f"    Email: {user['profile'].get('email')}")
                print(f"    Employee Number: {user['profile'].get('employeeNumber')}")
                
                # Now test with our actual ticket employee IDs
                print(f"\nTesting with ticket employee IDs:")
                test_employee_ids = ["13685751", "10493746", "7467777"]
                
                for emp_id in test_employee_ids:
                    print(f"\nSearching for employee number: {emp_id}")
                    
                    search_query = f'employeeNumber eq "{emp_id}"'
                    response = requests.get(
                        f"https://{okta_domain}/api/v1/users",
                        headers=headers,
                        params={'search': search_query},
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        users = response.json()
                        if users:
                            user = users[0]
                            print(f"  [FOUND] {user['profile'].get('displayName')} ({user['profile'].get('email')})")
                        else:
                            print(f"  [NOT FOUND] No user with employee number {emp_id}")
                    else:
                        print(f"  [ERROR] HTTP {response.status_code}")
                
            else:
                print(f"  [NO RESULTS] Query worked but no users found")
        else:
            print(f"  [ERROR] HTTP {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"  [EXCEPTION] {e}")

def main():
    """Main test function."""
    print("CORRECTED OKTA EMPLOYEE LOOKUP TEST")
    print("Testing with the correct search syntax")
    print()
    
    test_correct_employee_search()

if __name__ == "__main__":
    main()