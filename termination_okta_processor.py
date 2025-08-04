# termination_okta_processor.py - Process termination tickets and deactivate Okta users

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from config import get_solarwinds_credentials, get_okta_credentials, SAMANAGE_BASE_URL
from okta_termination import OktaTermination

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Termination subcategory ID (confirmed from find_termination_tickets.py)
TERMINATION_SUBCATEGORY_ID = 1574220  # "Termination" in Human Resources

def get_solarwinds_headers():
    """Get SolarWinds API headers."""
    token, _ = get_solarwinds_credentials()
    return {
        "X-Samanage-Authorization": f"Bearer {token}",
        "Accept": "application/vnd.samanage.v2.1+json"
    }

def fetch_active_termination_tickets():
    """Fetch active termination tickets that need processing."""
    logger.info("Fetching active termination tickets...")
    headers = get_solarwinds_headers()
    
    # Get tickets from termination subcategory that are not resolved/closed
    params = {
        "subcategory_id": TERMINATION_SUBCATEGORY_ID,
        "per_page": 100,
        "sort": "created_at",
        "sort_order": "desc"
    }
    
    try:
        response = requests.get(f"{SAMANAGE_BASE_URL}/incidents.json", 
                              headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            all_tickets = response.json()
            # Filter for active tickets (not resolved/closed)
            active_tickets = [
                ticket for ticket in all_tickets 
                if ticket.get('state') not in ['Resolved', 'Closed']
            ]
            logger.info(f"Found {len(active_tickets)} active termination tickets")
            return active_tickets
        else:
            logger.error(f"Error fetching tickets: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching termination tickets: {e}")
        return []

def extract_employee_from_ticket(ticket: Dict) -> Optional[Dict]:
    """Extract employee termination data from a ticket."""
    custom_fields = ticket.get('custom_fields_values', [])
    
    # Map field names to our data structure
    field_map = {
        'Employee to Terminate': 'employee_id',
        'Employee Department': 'department', 
        'Termination Date': 'termination_date',
        'Date to remove access': 'access_removal_date',
        'Term Type': 'termination_type',
        'Transfer Data': 'transfer_to_employee_id',
        'Additional Information': 'notes'
    }
    
    employee_data = {
        'ticket_number': ticket.get('number'),
        'ticket_title': ticket.get('name'),
        'ticket_state': ticket.get('state'),
        'created_at': ticket.get('created_at')
    }
    
    # Extract custom field values
    for field in custom_fields:
        field_name = field.get('name', '')
        field_value = field.get('value', '')
        
        if field_name in field_map and field_value:
            employee_data[field_map[field_name]] = field_value
    
    # Only return if we have the essential data
    if 'employee_id' in employee_data:
        logger.info(f"Extracted employee data for ID {employee_data['employee_id']} from ticket #{employee_data['ticket_number']}")
        return employee_data
    
    return None

def should_process_termination(employee_data: Dict) -> bool:
    """Determine if a termination should be processed based on dates."""
    today = datetime.now().date()
    
    # Check if access removal date is today or in the past
    access_date_str = employee_data.get('access_removal_date', '')
    if access_date_str:
        try:
            # Parse date (format: "Aug 01, 2025" or similar)
            access_date = datetime.strptime(access_date_str, "%b %d, %Y").date()
            if access_date <= today:
                logger.info(f"Employee {employee_data['employee_id']} access removal due: {access_date}")
                return True
        except ValueError:
            logger.warning(f"Could not parse access removal date: {access_date_str}")
    
    # Check termination date as fallback
    term_date_str = employee_data.get('termination_date', '')
    if term_date_str:
        try:
            term_date = datetime.strptime(term_date_str, "%b %d, %Y").date()
            # Process if termination was yesterday or earlier (grace period)
            if term_date <= today:
                logger.info(f"Employee {employee_data['employee_id']} termination date passed: {term_date}")
                return True
        except ValueError:
            logger.warning(f"Could not parse termination date: {term_date_str}")
    
    return False

def process_employee_termination(employee_data: Dict, test_mode: bool = True):
    """Process a single employee termination in Okta."""
    employee_id = employee_data['employee_id']
    logger.info(f"Processing termination for employee {employee_id}")
    
    # Initialize Okta client
    okta = OktaTermination()
    
    try:
        # Step 1: Find user in Okta by employee ID
        logger.info(f"Looking up user {employee_id} in Okta...")
        user = okta.find_user_by_employee_id(employee_id)
        
        if not user:
            logger.warning(f"User {employee_id} not found in Okta")
            return {
                'success': False,
                'error': 'User not found in Okta',
                'employee_id': employee_id
            }
        
        user_email = user.get('profile', {}).get('email', 'Unknown')
        logger.info(f"Found user: {user_email} (ID: {user['id']})")
        
        if test_mode:
            logger.info("TEST MODE: Would perform the following actions:")
            logger.info(f"  1. Clear all active sessions for {user_email}")
            logger.info(f"  2. Deactivate user account for {user_email}")
            logger.info(f"  3. Remove from all groups")
            return {
                'success': True,
                'test_mode': True,
                'user_email': user_email,
                'employee_id': employee_id,
                'actions': ['session_clear', 'deactivate', 'remove_groups']
            }
        
        # Step 2: Clear all user sessions (critical security step)
        logger.info(f"Clearing all sessions for user {user_email}...")
        session_result = okta.clear_user_sessions(user['id'])
        
        # Step 3: Deactivate the user
        logger.info(f"Deactivating user {user_email}...")
        deactivate_result = okta.deactivate_user(user['id'])
        
        # Step 4: Remove from all groups
        logger.info(f"Removing user {user_email} from all groups...")
        group_result = okta.remove_user_from_all_groups(user['id'])
        
        logger.info(f"Successfully processed termination for {user_email}")
        return {
            'success': True,
            'user_email': user_email,
            'employee_id': employee_id,
            'session_clear': session_result,
            'deactivation': deactivate_result,
            'group_removal': group_result
        }
        
    except Exception as e:
        logger.error(f"Error processing termination for {employee_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'employee_id': employee_id
        }

def update_ticket_status(ticket_number: str, status: str, comment: str):
    """Update the ticket status after processing."""
    # This would update the SolarWinds ticket
    # Implementation depends on your ticketing workflow
    logger.info(f"Would update ticket #{ticket_number} to {status}: {comment}")

def main(test_mode: bool = True):
    """Main termination processing function."""
    logger.info("Starting termination processing...")
    
    if test_mode:
        logger.warning("RUNNING IN TEST MODE - NO ACTUAL CHANGES WILL BE MADE")
    
    # Fetch active termination tickets
    tickets = fetch_active_termination_tickets()
    
    if not tickets:
        logger.info("No active termination tickets found")
        return
    
    processed_count = 0
    errors = []
    
    for ticket in tickets:
        # Extract employee data from ticket
        employee_data = extract_employee_from_ticket(ticket)
        
        if not employee_data:
            logger.warning(f"Could not extract employee data from ticket #{ticket.get('number')}")
            continue
        
        # Check if this termination should be processed today
        if not should_process_termination(employee_data):
            logger.info(f"Termination for employee {employee_data['employee_id']} not due yet")
            continue
        
        # Process the termination
        result = process_employee_termination(employee_data, test_mode)
        
        if result['success']:
            processed_count += 1
            if not test_mode:
                update_ticket_status(
                    employee_data['ticket_number'],
                    'In Progress',
                    f"Okta account deactivated for employee {employee_data['employee_id']}"
                )
        else:
            errors.append(result)
    
    # Summary
    logger.info(f"Processing complete. Processed: {processed_count}, Errors: {len(errors)}")
    
    if errors:
        logger.error("Errors encountered:")
        for error in errors:
            logger.error(f"  Employee {error['employee_id']}: {error.get('error', 'Unknown error')}")

if __name__ == "__main__":
    # Run in test mode by default for safety
    main(test_mode=True)
