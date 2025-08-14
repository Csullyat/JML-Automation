import logging
from ticket_processor import extract_user_email_from_ticket, extract_manager_email_from_ticket

# Configure logging to print to console
logging.basicConfig(level=logging.DEBUG)

# Example test tickets
sample_tickets = [
    {
        'ticket_number': '12345',
        'employee_to_terminate': 'jdoe',
        'transfer_data': 'manager1',
        'additional_info': ''
    },
    {
        'ticket_number': '12346',
        'employee_to_terminate': '13685751',  # Should trigger Okta lookup
        'transfer_data': 'manager2@filevine.com',
        'additional_info': ''
    },
    {
        'ticket_number': '12347',
        'employee_to_terminate': 'user3@filevine.com',
        'transfer_data': '',
        'additional_info': 'manager3@filevine.com'
    },
    {
        'ticket_number': '12348',
        'employee_to_terminate': '',
        'transfer_data': '',
        'additional_info': ''
    }
]

def run_tests():
    for ticket in sample_tickets:
        print(f"\nTesting ticket {ticket['ticket_number']}")
        user_email = extract_user_email_from_ticket(ticket)
        manager_email = extract_manager_email_from_ticket(ticket)
        print(f"  Extracted user email: {user_email}")
        print(f"  Extracted manager email: {manager_email}")

if __name__ == "__main__":
    run_tests()
