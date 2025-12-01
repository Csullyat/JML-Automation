#!/usr/bin/env python3

from jml_automation.services.okta import OktaService
import json

def test_employee_id_lookup():
    """Test Okta employee ID lookup for ticket 69988"""
    
    print("=== OKTA EMPLOYEE ID LOOKUP TEST ===")
    
    try:
        okta_service = OktaService.from_config()
        
        # Test the specific employee ID from ticket 69988
        employee_id = "7430764"
        print(f"Looking up employee ID: {employee_id}")
        
        # Test the lookup method
        result = okta_service.lookup_email_by_employee_id(employee_id)
        print(f"Lookup result: {result}")
        
        # Also test searching for Chris Nielsen variations
        print("\n=== SEARCHING FOR CHRIS NIELSEN VARIATIONS ===")
        search_terms = [
            'profile.displayName eq "Chris Nielsen"',
            'profile.displayName eq "Christopher Nielsen"', 
            'profile.employeeNumber eq "7430764"',
            'profile.email eq "christophernielsen@filevine.com"'
        ]
        
        for search_term in search_terms:
            try:
                results = okta_service.search_users(search_term)
                print(f"Search '{search_term}': {len(results)} results")
                
                for i, user in enumerate(results):
                    email = user.get('profile', {}).get('email', 'N/A')
                    display_name = user.get('profile', {}).get('displayName', 'N/A')
                    employee_number = user.get('profile', {}).get('employeeNumber', 'N/A')
                    status = user.get('status', 'N/A')
                    print(f"  User {i+1}: {email}")
                    print(f"    Display Name: '{display_name}'")
                    print(f"    Employee Number: {employee_number}")
                    print(f"    Status: {status}")
                    
            except Exception as e:
                print(f"Error with search '{search_term}': {e}")
        
        # Test if the correct email exists
        print(f"\n=== TESTING CORRECT EMAIL EXISTS ===")
        try:
            user = okta_service.get_user_by_email("christophernielsen@filevine.com")
            if user:
                display_name = user.get('profile', {}).get('displayName', 'N/A')
                employee_number = user.get('profile', {}).get('employeeNumber', 'N/A')
                status = user.get('status', 'N/A')
                print(f"✓ Found christophernielsen@filevine.com")
                print(f"  Display Name: '{display_name}'")
                print(f"  Employee Number: {employee_number}")
                print(f"  Status: {status}")
            else:
                print("✗ christophernielsen@filevine.com NOT FOUND")
        except Exception as e:
            print(f"Error checking christophernielsen@filevine.com: {e}")
            
        # Test if the wrong email exists
        print(f"\n=== TESTING WRONG EMAIL ===")
        try:
            user = okta_service.get_user_by_email("chrisnielsen@filevine.com")
            if user:
                display_name = user.get('profile', {}).get('displayName', 'N/A')
                employee_number = user.get('profile', {}).get('employeeNumber', 'N/A')
                status = user.get('status', 'N/A')
                print(f"✓ Found chrisnielsen@filevine.com (THIS IS WRONG)")
                print(f"  Display Name: '{display_name}'")
                print(f"  Employee Number: {employee_number}")
                print(f"  Status: {status}")
            else:
                print("✓ chrisnielsen@filevine.com does NOT exist (good!)")
        except Exception as e:
            print(f"Error checking chrisnielsen@filevine.com: {e}")
            
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == '__main__':
    test_employee_id_lookup()