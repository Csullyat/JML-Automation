#!/usr/bin/env python3
"""
Test different Okta filter syntax variations to find the working one.
"""

import logging
import requests
from config import get_okta_token, get_okta_domain

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_okta_filter_variations():
    """Test different filter syntax variations."""
    print("=" * 80)
    print("TESTING OKTA FILTER SYNTAX VARIATIONS")
    print("=" * 80)
    
    okta_token = get_okta_token()
    okta_domain = get_okta_domain()
    
    headers = {
        'Authorization': f'SSWS {okta_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Test with the known working employee number first
    known_employee_number = "2523"  # Dallas Clinger
    
    print(f"Testing with known employee number: {known_employee_number}")
    print("(We know this exists from our sample data)")
    print()
    
    # Different syntax variations to try
    variations = [
        # Variation 1: filter parameter with profile prefix
        {
            'name': 'Filter with profile.employeeNumber',
            'params': {'filter': f'profile.employeeNumber eq "{known_employee_number}"'}
        },
        # Variation 2: filter parameter without profile prefix  
        {
            'name': 'Filter with employeeNumber only',
            'params': {'filter': f'employeeNumber eq "{known_employee_number}"'}
        },
        # Variation 3: search parameter
        {
            'name': 'Search parameter',
            'params': {'search': f'profile.employeeNumber eq "{known_employee_number}"'}
        },
        # Variation 4: q parameter (general search)
        {
            'name': 'Query parameter',
            'params': {'q': known_employee_number}
        },
        # Variation 5: Different field variations
        {
            'name': 'Filter with profile.employee_number',
            'params': {'filter': f'profile.employee_number eq "{known_employee_number}"'}
        }
    ]
    
    working_syntax = None
    
    for variation in variations:
        print(f"Testing: {variation['name']}")
        print(f"  Parameters: {variation['params']}")
        
        try:
            response = requests.get(
                f"https://{okta_domain}/api/v1/users",
                headers=headers,
                params=variation['params'],
                timeout=30
            )
            
            print(f"  Status Code: {response.status_code}")
            
            if response.status_code == 200:
                users = response.json()
                if users:
                    user = users[0]
                    print(f"  [SUCCESS] Found user!")
                    print(f"    Name: {user['profile'].get('displayName')}")
                    print(f"    Email: {user['profile'].get('email')}")
                    print(f"    Employee Number: {user['profile'].get('employeeNumber')}")
                    working_syntax = variation
                    break  # Found working syntax
                else:
                    print(f"  [NO RESULTS] Query worked but returned no users")
            elif response.status_code == 400:
                error_data = response.json()
                print(f"  [BAD REQUEST] {error_data.get('errorSummary', 'Unknown error')}")
            else:
                print(f"  [ERROR] HTTP {response.status_code}")
                if response.text:
                    print(f"    Response: {response.text[:200]}")
                    
        except Exception as e:
            print(f"  [EXCEPTION] {e}")
        
        print()
    
    return working_syntax

def test_with_ticket_employee_ids(working_syntax):
    """Test the working syntax with our ticket employee IDs."""
    if not working_syntax:
        print("No working syntax found - cannot test ticket employee IDs")
        return []
    
    print("=" * 80)
    print("TESTING WITH TICKET EMPLOYEE IDs")
    print("=" * 80)
    
    okta_token = get_okta_token()
    okta_domain = get_okta_domain()
    
    headers = {
        'Authorization': f'SSWS {okta_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Employee IDs from our ticket data
    ticket_employee_ids = [
        "13685751",  # User from ticket
        "10493746",  # Manager from ticket
        "7467777",   # Manager from other tickets
        "13178254",  # Another user
        "13203385"   # Another user
    ]
    
    results = []
    
    for employee_id in ticket_employee_ids:
        print(f"Searching for Employee ID: {employee_id}")
        
        # Build parameters based on working syntax, replacing the employee number
        params = {}
        for key, value in working_syntax['params'].items():
            if 'eq' in str(value):
                # Replace the employee number in the filter/search string
                new_value = str(value).replace('"2523"', f'"{employee_id}"')
                params[key] = new_value
            else:
                params[key] = employee_id
        
        try:
            response = requests.get(
                f"https://{okta_domain}/api/v1/users",
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                users = response.json()
                if users:
                    user = users[0]
                    result = {
                        'employee_id': employee_id,
                        'found': True,
                        'name': user['profile'].get('displayName'),
                        'email': user['profile'].get('email'),
                        'login': user['profile'].get('login'),
                        'employee_number': user['profile'].get('employeeNumber')
                    }
                    print(f"  [FOUND] {result['name']} ({result['email']})")
                    results.append(result)
                else:
                    result = {
                        'employee_id': employee_id,
                        'found': False,
                        'error': 'No user found with this employee ID'
                    }
                    print(f"  [NOT FOUND] No user with employee ID {employee_id}")
                    results.append(result)
            else:
                result = {
                    'employee_id': employee_id,
                    'found': False,
                    'error': f'HTTP {response.status_code}'
                }
                print(f"  [ERROR] HTTP {response.status_code}")
                results.append(result)
                
        except Exception as e:
            result = {
                'employee_id': employee_id,
                'found': False,
                'error': str(e)
            }
            print(f"  [EXCEPTION] {e}")
            results.append(result)
    
    return results

def main():
    """Main test function."""
    print("OKTA FILTER SYNTAX DISCOVERY")
    print("Finding the correct API syntax for employee number lookups")
    print()
    
    # First, find working syntax with known data
    working_syntax = test_okta_filter_variations()
    
    if working_syntax:
        print("=" * 80)
        print(f"SUCCESS! Working syntax found: {working_syntax['name']}")
        print(f"Parameters: {working_syntax['params']}")
        print("=" * 80)
        
        # Now test with ticket employee IDs
        results = test_with_ticket_employee_ids(working_syntax)
        
        # Summary
        found_count = sum(1 for r in results if r['found'])
        print(f"\nFINAL RESULTS:")
        print(f"Employee IDs from tickets tested: {len(results)}")
        print(f"Users found in Okta: {found_count}")
        
        if found_count > 0:
            print(f"\nSUCCESSFUL LOOKUPS:")
            for result in results:
                if result['found']:
                    print(f"  {result['employee_id']} -> {result['email']} ({result['name']})")
        
        not_found = [r for r in results if not r['found']]
        if not_found:
            print(f"\nNOT FOUND IN OKTA:")
            for result in not_found:
                print(f"  {result['employee_id']}: {result['error']}")
        
        if found_count > 0:
            print(f"\n✅ SOLUTION FOUND!")
            print(f"Use this syntax in the fixed ticket_processor.py:")
            print(f"params = {working_syntax['params']}")
        
    else:
        print("❌ No working syntax found.")
        print("This suggests either:")
        print("1. Employee numbers aren't searchable in your Okta instance")
        print("2. Different field name is used")
        print("3. API permissions issue")
        print("4. Employee numbers are stored differently")

if __name__ == "__main__":
    main()