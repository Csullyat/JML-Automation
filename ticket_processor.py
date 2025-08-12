# ticket_processor.py - Bridge between enterprise orchestrator and termination extractor

import logging
from typing import List, Dict, Optional
from termination_extractor import fetch_tickets, filter_termination_users

logger = logging.getLogger(__name__)

def fetch_termination_tickets() -> List[Dict]:
    """
    Fetch and filter termination tickets for processing.
    This is a bridge function that uses the termination_extractor functionality.
    """
    try:
        logger.info("Fetching termination tickets from SolarWinds")
        
        # Use the existing fetch_tickets function
        all_tickets = fetch_tickets()
        
        if not all_tickets:
            logger.info("No tickets found")
            return []
        
        # Use the existing filter function to get parsed termination users
        filtered_users = filter_termination_users(all_tickets)
        
        logger.info(f"Found {len(filtered_users)} actionable termination tickets")
        return filtered_users
        
    except Exception as e:
        logger.error(f"Failed to fetch termination tickets: {e}")
        return []

def extract_user_email_from_ticket(ticket: Dict) -> Optional[str]:
    """
    Extract user email from a parsed termination ticket.
    
    Args:
        ticket: Parsed ticket dict from termination_extractor
        
    Returns:
        User email if found, None otherwise
    """
    try:
        # The termination_extractor stores employee ID in 'employee_to_terminate'
        # This could be an email or employee ID
        employee_to_terminate = ticket.get('employee_to_terminate', '').strip()
        
        if not employee_to_terminate:
            logger.warning(f"No employee_to_terminate found in ticket {ticket.get('ticket_number', 'unknown')}")
            return None
        
        # Check if it's already an email
        if '@' in employee_to_terminate:
            logger.info(f"Found email in ticket: {employee_to_terminate}")
            return employee_to_terminate
        
        # If it's not an email, we might need to look it up or convert it
        # For now, assume it needs @filevine.com appended if it looks like a username
        if employee_to_terminate and not '@' in employee_to_terminate:
            # Check if it looks like a username (no spaces, alphanumeric)
            if employee_to_terminate.replace('.', '').replace('_', '').replace('-', '').isalnum():
                email = f"{employee_to_terminate}@filevine.com"
                logger.info(f"Converted employee ID '{employee_to_terminate}' to email: {email}")
                return email
        
        logger.warning(f"Could not extract valid email from employee_to_terminate: '{employee_to_terminate}'")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting user email from ticket: {e}")
        return None

def extract_manager_email_from_ticket(ticket: Dict) -> Optional[str]:
    """
    Extract manager email from a parsed termination ticket.
    
    Args:
        ticket: Parsed ticket dict from termination_extractor
        
    Returns:
        Manager email if found, None otherwise
    """
    try:
        # Look for manager information in various fields
        # Check transfer_data field first (common place for manager info)
        transfer_data = ticket.get('transfer_data', '').strip()
        
        if transfer_data and '@' in transfer_data:
            # Extract email from transfer_data
            words = transfer_data.split()
            for word in words:
                if '@' in word and 'filevine.com' in word:
                    logger.info(f"Found manager email in transfer_data: {word}")
                    return word.strip('.,;:')
        
        # Check additional_info field
        additional_info = ticket.get('additional_info', '').strip()
        if additional_info and '@' in additional_info:
            words = additional_info.split()
            for word in words:
                if '@' in word and 'filevine.com' in word:
                    logger.info(f"Found manager email in additional_info: {word}")
                    return word.strip('.,;:')
        
        # Could also check for manager name and try to convert to email
        # For now, return None if no email found
        logger.info(f"No manager email found in ticket {ticket.get('ticket_number', 'unknown')}")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting manager email from ticket: {e}")
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
