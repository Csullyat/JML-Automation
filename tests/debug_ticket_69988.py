#!/usr/bin/env python3

from jml_automation.parsers.solarwinds_parser import fetch_ticket
from jml_automation.services.solarwinds import SolarWindsService
from jml_automation.services.okta import OktaService
import json

def main():
    # Fetch ticket data
    sw_service = SolarWindsService.from_config()
    okta_service = OktaService.from_config()
    ticket_data = fetch_ticket("69988")

    print('=== TICKET 69988 DEBUG ===')
    print(f'Raw ticket data keys: {list(ticket_data.keys()) if ticket_data else "None"}')
    print(f'Ticket Name: {ticket_data.get("name", "N/A")}')
    print(f'Ticket ID: {ticket_data.get("id", "N/A")}')
    print(f'Full ticket data: {json.dumps(ticket_data, indent=2) if ticket_data and len(str(ticket_data)) < 1000 else "Too large or None"}')

    # Extract display name like our workflow does
    display_name = None
    ticket_name = ticket_data.get('name', '') if ticket_data else ''
    if 'Employee Termination' in ticket_name:
        display_name = ticket_name.replace('Employee Termination - ', '').strip()

    print(f'Extracted Display Name: "{display_name}"')

    # Try to search in Okta with the display name
    if display_name:
        print(f'\nSearching Okta for display name: "{display_name}"')
        try:
            search_results = okta_service.search_users(f'profile.displayName eq "{display_name}"')
            print(f'Exact match results: {len(search_results)} users found')
            
            for i, user in enumerate(search_results):
                email = user.get('profile', {}).get('email', 'N/A')
                user_display_name = user.get('profile', {}).get('displayName', 'N/A')
                status = user.get('status', 'N/A')
                print(f'  User {i+1}: {email} (Display: "{user_display_name}", Status: {status})')
                
            # Try fuzzy search
            if not search_results:
                print(f'\nNo exact match, trying fuzzy search...')
                first_name = display_name.split()[0] if display_name.split() else ''
                fuzzy_results = okta_service.search_users(f'profile.displayName pr and profile.displayName sw "{first_name}"')
                print(f'Fuzzy search results: {len(fuzzy_results)} users found')
                
                for i, user in enumerate(fuzzy_results[:5]):  # Show first 5
                    email = user.get('profile', {}).get('email', 'N/A')
                    user_display_name = user.get('profile', {}).get('displayName', 'N/A')
                    status = user.get('status', 'N/A')
                    print(f'  Fuzzy {i+1}: {email} (Display: "{user_display_name}", Status: {status})')
            
        except Exception as e:
            print(f'Error searching Okta: {e}')

    # Also try searching for different variations of the email
    print(f'\n=== TESTING EMAIL VARIATIONS ===')
    email_variations = [
        'christopherneilson@filevine.com',
        'chrisneilson@filevine.com',
        'christopher.neilson@filevine.com',
        'chris.neilson@filevine.com',
        'christophernielson@filevine.com',
        'chrisnielson@filevine.com'
    ]
    
    for email in email_variations:
        try:
            user = okta_service.get_user_by_email(email)
            if user:
                display_name = user.get('profile', {}).get('displayName', 'N/A')
                status = user.get('status', 'N/A')
                print(f'✓ FOUND: {email} -> Display: "{display_name}", Status: {status}')
            else:
                print(f'✗ Not found: {email}')
        except Exception as e:
            print(f'✗ Error checking {email}: {e}')
            
    # Try searching by first/last name variations
    print(f'\n=== SEARCHING BY NAME VARIATIONS ===')
    name_variations = [
        'Christopher Neilson',
        'Chris Neilson', 
        'Christopher Nielsen',
        'Chris Nielsen'
    ]
    
    for name in name_variations:
        try:
            results = okta_service.search_users(f'profile.displayName eq "{name}"')
            if results:
                for user in results:
                    email = user.get('profile', {}).get('email', 'N/A')
                    status = user.get('status', 'N/A')
                    print(f'✓ FOUND by name "{name}": {email} (Status: {status})')
            else:
                print(f'✗ No results for name: "{name}"')
        except Exception as e:
            print(f'✗ Error searching name "{name}": {e}')

if __name__ == '__main__':
    main()