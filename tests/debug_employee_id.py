#!/usr/bin/env python3

from jml_automation.services.okta import OktaService

def main():
    okta_service = OktaService.from_config()
    
    print("=== DEBUGGING EMPLOYEE ID 7430764 ===")
    
    # Check what employee ID 7430764 resolves to
    email = okta_service.lookup_email_by_employee_id("7430764")
    print(f"Employee ID 7430764 resolves to: {email}")
    
    # Check both emails we're interested in
    emails_to_check = [
        'christophernielsen@filevine.com',
        'chrisnielsen@filevine.com'
    ]
    
    for email in emails_to_check:
        try:
            user = okta_service.get_user_by_email(email)
            if user:
                employee_number = user.get('profile', {}).get('employeeNumber', 'N/A')
                display_name = user.get('profile', {}).get('displayName', 'N/A')
                status = user.get('status', 'N/A')
                print(f"✓ {email}:")
                print(f"  Employee Number: {employee_number}")
                print(f"  Display Name: '{display_name}'")
                print(f"  Status: {status}")
            else:
                print(f"✗ {email}: Not found")
        except Exception as e:
            print(f"✗ {email}: Error - {e}")
    
    # Search for similar names
    print(f"\n=== SEARCHING FOR SIMILAR NAMES ===")
    search_terms = [
        'Chris Nielsen',
        'Christopher Nielsen', 
        'Chris Neilson',
        'Christopher Neilson'
    ]
    
    for name in search_terms:
        try:
            results = okta_service.search_users(f'profile.displayName eq "{name}"')
            if results:
                for user in results:
                    email = user.get('profile', {}).get('email', 'N/A')
                    employee_number = user.get('profile', {}).get('employeeNumber', 'N/A')
                    status = user.get('status', 'N/A')
                    print(f"✓ Found '{name}': {email} (Employee: {employee_number}, Status: {status})")
            else:
                print(f"✗ No results for: '{name}'")
        except Exception as e:
            print(f"✗ Error searching '{name}': {e}")

if __name__ == '__main__':
    main()