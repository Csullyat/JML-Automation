# search_tickets.py - Search for specific ticket numbers

import requests
from config import get_solarwinds_credentials, SAMANAGE_BASE_URL

def search_specific_tickets(ticket_numbers):
    """Search for specific ticket numbers."""
    token, _ = get_solarwinds_credentials()
    headers = {
        "X-Samanage-Authorization": f"Bearer {token}",
        "Accept": "application/vnd.samanage.v2.1+json"
    }
    
    found_tickets = []
    
    for ticket_num in ticket_numbers:
        print(f"Searching for ticket #{ticket_num}...")
        
        # Search by ticket number
        params = {
            "number": ticket_num,
            "per_page": 10
        }
        
        try:
            response = requests.get(f"{SAMANAGE_BASE_URL}/incidents.json", 
                                  headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                tickets = response.json()
                if tickets:
                    for ticket in tickets:
                        if str(ticket.get('number')) == str(ticket_num):
                            found_tickets.append(ticket)
                            print(f"FOUND: Ticket #{ticket['number']}")
                            print(f"  Title: {ticket.get('name', 'No title')}")
                            print(f"  State: {ticket.get('state')}")
                            print(f"  Category: {ticket.get('category', {}).get('name') if ticket.get('category') else 'None'}")
                            print(f"  Subcategory: {ticket.get('subcategory', {}).get('name') if ticket.get('subcategory') else 'None'}")
                            print(f"  Created: {ticket.get('created_at')}")
                            
                            # Check if it's a termination ticket
                            subcategory_id = ticket.get('subcategory', {}).get('id') if ticket.get('subcategory') else None
                            if subcategory_id == 1574220:
                                print(f"  *** THIS IS A TERMINATION TICKET ***")
                            else:
                                print(f"  Subcategory ID: {subcategory_id} (not termination)")
                            print()
                else:
                    print(f"  No ticket found with number {ticket_num}")
            else:
                print(f"  Error searching for {ticket_num}: {response.status_code}")
                
        except Exception as e:
            print(f"  Error searching for {ticket_num}: {e}")
    
    return found_tickets

if __name__ == "__main__":
    # Search for the specific tickets
    target_tickets = ["56636", "56634"]
    found = search_specific_tickets(target_tickets)
    
    print(f"\nSummary: Found {len(found)} of {len(target_tickets)} requested tickets")
