#!/usr/bin/env python3
"""Detailed analysis of termination tickets"""

from termination_extractor import fetch_tickets, filter_termination_users, parse_termination_ticket
import json
from collections import Counter

def detailed_ticket_analysis():
    """Comprehensive analysis of termination tickets."""
    
    print('🔍 COMPREHENSIVE TERMINATION TICKET ANALYSIS')
    print('=' * 80)

    # Fetch more tickets for comprehensive view
    print('Fetching tickets from SolarWinds (expanded search)...')
    all_tickets = fetch_tickets(per_page=100, max_pages=10)  # Get more tickets

    print(f'📊 RAW TICKET STATISTICS:')
    print(f'Total tickets fetched: {len(all_tickets)}')
    
    # Analyze ticket states
    if all_tickets:
        states = [ticket.get('state', 'Unknown') for ticket in all_tickets]
        state_counts = Counter(states)
        print(f'\n📈 TICKET STATES DISTRIBUTION:')
        for state, count in state_counts.most_common():
            marker = '👉' if state == 'Awaiting Input' else '  '
            print(f'{marker} {state}: {count} tickets')
    
    # Analyze categories/subcategories
    categories = []
    for ticket in all_tickets:
        cat = ticket.get('category', {}).get('name', 'Unknown') if ticket.get('category') else 'Unknown'
        subcat = ticket.get('subcategory', {}).get('name', 'Unknown') if ticket.get('subcategory') else 'Unknown'
        categories.append(f"{cat} > {subcat}")
    
    if categories:
        cat_counts = Counter(categories)
        print(f'\n📁 CATEGORY DISTRIBUTION:')
        for cat, count in cat_counts.most_common(5):  # Top 5
            print(f'   {cat}: {count} tickets')

    # Filter for active termination requests
    print(f'\n🎯 FILTERING FOR ACTIVE TERMINATIONS...')
    active_terminations = filter_termination_users(all_tickets)

    print(f'\n📋 ACTIVE TERMINATION TICKETS DETAILS:')
    print(f'Total active termination tickets: {len(active_terminations)}')

    if active_terminations:
        for i, ticket in enumerate(active_terminations, 1):
            print(f'\n{"="*60}')
            print(f'TICKET #{i}: {ticket.get("ticket_number", "Unknown")}')
            print(f'{"="*60}')
            print(f'📧 Employee to Terminate: {ticket.get("employee_to_terminate", "Not specified")}')
            print(f'🎫 Ticket ID: {ticket.get("ticket_id", "Unknown")}')
            print(f'📊 State: {ticket.get("ticket_state", "Unknown")}')
            print(f'📅 Created: {ticket.get("ticket_created", "Unknown")}')
            print(f'📁 Category: {ticket.get("category", "Unknown")} > {ticket.get("subcategory", "Unknown")}')
            
            # Show all available fields for this ticket
            print(f'\n📝 ALL TICKET FIELDS:')
            for key, value in ticket.items():
                if key not in ['ticket_number', 'ticket_id', 'ticket_state', 'ticket_created', 'category', 'subcategory', 'employee_to_terminate']:
                    print(f'   {key}: {value}')
                    
            # Show if we can find the original ticket for more details
            original_ticket = None
            for orig in all_tickets:
                if str(orig.get('number')) == str(ticket.get('ticket_number')):
                    original_ticket = orig
                    break
                    
            if original_ticket:
                print(f'\n🔍 ADDITIONAL ORIGINAL TICKET DATA:')
                print(f'   Requester: {original_ticket.get("requester", {}).get("name", "Unknown")}')
                print(f'   Assignee: {original_ticket.get("assignee", {}).get("name", "Unassigned")}')
                print(f'   Priority: {original_ticket.get("priority", "Unknown")}')
                print(f'   Description preview: {str(original_ticket.get("description", ""))[:100]}...')
    else:
        print('\n✅ No active termination tickets found in "Awaiting Input" state')

    print(f'\n{"="*80}')
    return active_terminations

if __name__ == "__main__":
    detailed_ticket_analysis()
