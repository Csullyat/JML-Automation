import logging
from microsoft_termination import MicrosoftTermination
from okta_termination import OktaTermination
from termination_extractor import fetch_tickets
from ticket_processor import extract_user_email_from_ticket, extract_manager_email_from_ticket

logging.basicConfig(level=logging.INFO)

def run_microsoft_and_okta_termination_test():
    print("Fetching up to 6000 tickets from SolarWinds...")
    all_tickets = fetch_tickets(per_page=200, max_pages=30)
    print(f"Total tickets fetched: {len(all_tickets)}")
    # Filter for actionable tickets
    filtered = []
    for t in all_tickets:
        state = t.get('state', '').strip().lower()
        assignee = t.get('assignee', '').strip().lower() if isinstance(t.get('assignee', ''), str) else ''
        if not assignee and isinstance(t.get('assignee', None), dict):
            assignee = t['assignee'].get('name', '').strip().lower()
        if state == 'awaiting input' and assignee == 'terminations':
            filtered.append(t)
    print(f"Tickets assigned to 'Terminations' and state 'Awaiting Input': {len(filtered)}")
    if not filtered:
        print("No actionable tickets found.")
        return
    ms_term = MicrosoftTermination()
    okta_term = OktaTermination()
    for i, ticket in enumerate(filtered):
        user_email = extract_user_email_from_ticket(ticket)
        manager_email = extract_manager_email_from_ticket(ticket)
        print(f"\nTicket #{ticket.get('number', 'unknown')}")
        print(f"  User email: {user_email}")
        print(f"  Manager email: {manager_email}")
        if user_email and manager_email:
            print("  Running Microsoft 365 termination...")
            ms_result = ms_term.execute_complete_termination(user_email, manager_email)
            print(f"  Microsoft 365 Result: {ms_result}")
            print("  Running Okta group removal...")
            okta_result = okta_term.execute_complete_termination(user_email)
            print(f"  Okta Result: {okta_result}")
        else:
            print("  Skipping: missing user or manager email.")
        if i == 0:
            print("Sample ticket fields:")
            for k, v in ticket.items():
                print(f"    {k}: {v}")
        # For safety, only run on the first ticket unless you want to process all
        break

if __name__ == "__main__":
    run_microsoft_and_okta_termination_test()
