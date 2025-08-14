import logging
from termination_extractor import fetch_tickets
from ticket_processor import extract_user_email_from_ticket, extract_manager_email_from_ticket

# Configure logging to print to console
logging.basicConfig(level=logging.INFO)

def filter_awaiting_input_terminations(tickets):
    filtered = []
    for t in tickets:
        state = t.get('state', '').strip().lower()
        assignee = t.get('assignee', '').strip().lower() if isinstance(t.get('assignee', ''), str) else ''
        # Some APIs may return assignee as a dict
        if not assignee and isinstance(t.get('assignee', None), dict):
            assignee = t['assignee'].get('name', '').strip().lower()
        if state == 'awaiting input' and assignee == 'terminations':
            filtered.append(t)
    return filtered

def run_test():
    print("Fetching up to 6000 tickets from SolarWinds...")
    all_tickets = fetch_tickets(per_page=200, max_pages=30)  # 200 * 30 = 6000
    print(f"Total tickets fetched: {len(all_tickets)}")
    filtered = filter_awaiting_input_terminations(all_tickets)
    print(f"Tickets assigned to 'Terminations' and state 'Awaiting Input': {len(filtered)}")
    for i, ticket in enumerate(filtered):
        user_email = extract_user_email_from_ticket(ticket)
        manager_email = extract_manager_email_from_ticket(ticket)
        print(f"\nTicket #{ticket.get('number', 'unknown')}")
        print(f"  User email: {user_email}")
        print(f"  Manager email: {manager_email}")
        if i == 0:
            print("Sample ticket fields:")
            for k, v in ticket.items():
                print(f"    {k}: {v}")

if __name__ == "__main__":
    run_test()
