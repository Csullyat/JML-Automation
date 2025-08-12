#!/usr/bin/env python3
"""Test fetch of termination tickets"""

from termination_extractor import fetch_tickets, filter_termination_users
import json

def test_ticket_fetch():
    """Test fetching and filtering termination tickets."""
    
    print('🔍 FETCHING TERMINATION TICKETS - TEST MODE')
    print('=' * 60)

    # Fetch tickets with termination subcategory
    print('Fetching tickets from SolarWinds...')
    all_tickets = fetch_tickets(per_page=50, max_pages=5)  # Limited fetch for testing

    print(f'Raw tickets fetched: {len(all_tickets)}')

    # Filter for active termination requests
    print('\nFiltering for "Awaiting Input" termination tickets...')
    active_terminations = filter_termination_users(all_tickets)

    print(f'\n📊 RESULTS:')
    print(f'Total active termination tickets: {len(active_terminations)}')

    if active_terminations:
        print('\n📋 ACTIVE TERMINATION TICKETS:')
        for i, ticket in enumerate(active_terminations, 1):
            print(f'\n{i}. Ticket #{ticket.get("ticket_number", "Unknown")}')
            print(f'   Employee: {ticket.get("employee_to_terminate", "Not specified")}')
            print(f'   State: {ticket.get("ticket_state", "Unknown")}')
            print(f'   Created: {ticket.get("ticket_created", "Unknown")}')
            print(f'   Category: {ticket.get("category", "Unknown")} > {ticket.get("subcategory", "Unknown")}')
            
            # Show if termination date is specified
            if ticket.get("termination_date"):
                print(f'   Termination Date: {ticket.get("termination_date")}')
    else:
        print('\n✅ No active termination tickets found in "Awaiting Input" state')

    print('\n' + '=' * 60)
    return active_terminations

if __name__ == "__main__":
    test_ticket_fetch()
