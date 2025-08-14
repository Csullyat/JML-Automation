# ticket_processor.py - Bridge between enterprise orchestrator and termination extractor

import logging
import requests
from typing import List, Dict, Optional
from termination_extractor import fetch_tickets, filter_termination_users
from config import get_okta_token, get_okta_domain

logger = logging.getLogger(__name__)

# Cache for Okta lookups to avoid repeated API calls
_okta_lookup_cache = {}

def fetch_termination_tickets() -> List[Dict]:
    """
    Fetch and filter termination tickets for processing.
    This is a bridge function that uses the termination_extractor functionality.
    """
    try:
        logger.info("Fetching termination tickets from SolarWinds")
        # Import here to avoid circular import
        from termination_extractor import fetch_tickets, filter_termination_users
        all_tickets = fetch_tickets()
        if not all_tickets:
            logger.info("No tickets found")
            return []
        filtered_users = filter_termination_users(all_tickets)
        logger.info(f"Found {len(filtered_users)} actionable termination tickets")
        return filtered_users
    except Exception as e:
        logger.error(f"Failed to fetch termination tickets: {e}")
        return []

def extract_user_email_from_ticket(ticket: Dict) -> Optional[str]:
    """
    Extract user email from a parsed termination ticket.
    Returns user email if found, None otherwise.
    """
    try:
        # Prefer custom_fields_values if present
        custom_fields = ticket.get('custom_fields_values')
        if custom_fields:
            for field in custom_fields:
                if field.get('name', '').strip().lower() == 'employee to terminate':
                    user_obj = field.get('user')
                    if user_obj and isinstance(user_obj, dict):
                        email = user_obj.get('email')
                        if email:
                            return email.lower()
                    value = field.get('value')
                    if value and '@' in str(value):
                        return str(value).lower()
        # Fallback to legacy fields
        employee_to_terminate = ticket.get('employee_to_terminate', '').strip()
        logger.debug(f"Raw employee_to_terminate field: '{employee_to_terminate}'")
        if not employee_to_terminate:
            logger.warning(f"No employee_to_terminate found in ticket {ticket.get('ticket_number', 'unknown')}")
            return None
        if '@' in employee_to_terminate:
            return employee_to_terminate.lower()
        if employee_to_terminate.isdigit():
            email = lookup_okta_email(employee_to_terminate)
            if email:
                return email
            logger.warning(f"Employee ID {employee_to_terminate} not found in Okta for ticket {ticket.get('ticket_number', 'unknown')}")
            return None
        if employee_to_terminate.isalnum() and not employee_to_terminate.isdigit():
            email = f"{employee_to_terminate.lower()}@filevine.com"
            logger.info(f"Converted username '{employee_to_terminate}' to email '{email}'")
            return email
        logger.warning(f"Unrecognized employee_to_terminate format: '{employee_to_terminate}' in ticket {ticket.get('ticket_number', 'unknown')}")
        return None
    except Exception as e:
        logger.error(f"Error extracting user email from ticket: {e}")
        return None


def extract_manager_email_from_ticket(ticket: Dict) -> Optional[str]:
    """
    Extract manager email from a parsed termination ticket.
    Returns manager email if found, None otherwise.
    """
    try:
        # Prefer custom_fields_values if present
        custom_fields = ticket.get('custom_fields_values')
        if custom_fields:
            for field in custom_fields:
                if field.get('name', '').strip().lower() == 'transfer data':
                    user_obj = field.get('user')
                    if user_obj and isinstance(user_obj, dict):
                        email = user_obj.get('email')
                        if email:
                            return email.lower()
                    value = field.get('value')
                    if value and '@' in str(value):
                        return str(value).lower()
        # Fallback to legacy fields
        transfer_data = ticket.get('transfer_data', '').strip()
        logger.debug(f"Raw transfer_data field: '{transfer_data}'")
        if transfer_data:
            if '@' in transfer_data:
                return transfer_data.lower()
            if transfer_data.isdigit():
                email = lookup_okta_email(transfer_data)
                if email:
                    return email
                logger.warning(f"Manager ID {transfer_data} not found in Okta for ticket {ticket.get('ticket_number', 'unknown')}")
            elif transfer_data.isalnum():
                email = f"{transfer_data.lower()}@filevine.com"
                logger.info(f"Converted manager username '{transfer_data}' to email '{email}'")
                return email
        additional_info = ticket.get('additional_info', '').strip()
        logger.debug(f"Raw additional_info field: '{additional_info}'")
        if additional_info and '@' in additional_info:
            return additional_info.lower()
        logger.warning(f"No manager email found in ticket {ticket.get('ticket_number', 'unknown')}")
        return None
    except Exception as e:
        logger.error(f"Error extracting manager email from ticket: {e}")
        return None


def lookup_okta_email(employee_id: str) -> Optional[str]:
    """
    Lookup user email in Okta by employee ID, with caching.
    """
    if not employee_id:
        return None
    if employee_id in _okta_lookup_cache:
        return _okta_lookup_cache[employee_id]
    try:
        # Import here to avoid circular import
        from okta_termination import OktaTermination
        okta = OktaTermination()
        email = okta.lookup_email_by_employee_id(employee_id)
        if email:
            _okta_lookup_cache[employee_id] = email
        return email
    except Exception as e:
        logger.error(f"Okta lookup failed for employee_id {employee_id}: {e}")
        return None

def update_ticket_status(ticket_id: str, status: str, notes: str = "") -> bool:
    """
    Update ticket status in SolarWinds Service Desk.
    
    Args:
        ticket_id: Ticket ID to update
        status: New status (e.g., "Resolved", "Closed")
        notes: Optional notes to add to ticket
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # TODO: Implement actual ticket update functionality
        # This would use the SolarWinds API to update the ticket
        logger.info(f"Would update ticket {ticket_id} to status '{status}'")
        if notes:
            logger.info(f"Would add notes: {notes}")
        
        # For now, just log that we would update it
        return True
        
    except Exception as e:
        logger.error(f"Error updating ticket {ticket_id}: {e}")
        return False