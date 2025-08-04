# ticket_processor.py - Service desk ticket processing for termination requests

import logging
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from config import get_solarwinds_credentials, SAMANAGE_BASE_URL

logger = logging.getLogger(__name__)

def get_solarwinds_headers():
    """Get headers for SolarWinds Service Desk API - same as working project."""
    token, _ = get_solarwinds_credentials()  # Returns tuple (token, "")
    return {
        "X-Samanage-Authorization": f"Bearer {token}",
        "Accept": "application/vnd.samanage.v2.1+json",
        "Content-Type": "application/json"
    }

def fetch_termination_tickets(days_back: int = 7) -> List[Dict[str, Any]]:
    """
    Fetch termination tickets from SolarWinds Service Desk.
    
    Args:
        days_back: Number of days to look back for tickets
        
    Returns:
        List of ticket dictionaries
    """
    try:
        base_url = SAMANAGE_BASE_URL
        headers = get_solarwinds_headers()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Search for termination-related tickets
        params = {
            'created[]': f'{start_date.strftime("%Y-%m-%d")}..{end_date.strftime("%Y-%m-%d")}',
            'state[]': 'New,In Progress,Assigned',  # Only active tickets
            'per_page': 100
        }
        
        logger.info(f"Fetching termination tickets from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        response = requests.get(
            f"{base_url}/incidents.json",
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            tickets_data = response.json()
            tickets = tickets_data.get('data', [])
            logger.info(f"Retrieved {len(tickets)} tickets from Service Desk")
            return tickets
        else:
            logger.error(f"Failed to fetch tickets: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"Exception fetching tickets: {str(e)}")
        return []

def filter_termination_requests(tickets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter tickets to find termination requests and extract user information.
    
    Args:
        tickets: List of all tickets from service desk
        
    Returns:
        List of termination request dictionaries with extracted user info
    """
    termination_requests = []
    termination_keywords = [
        'termination', 'terminate', 'offboard', 'off-board', 'offboarding',
        'departure', 'leaving', 'disable account', 'deactivate account',
        'employee leaving', 'last day', 'end employment', 'final day'
    ]
    
    logger.info(f"Filtering {len(tickets)} tickets for termination requests...")
    
    for ticket in tickets:
        try:
            ticket_id = ticket.get('id')
            ticket_number = ticket.get('number')
            title = ticket.get('name', '').lower()
            description = ticket.get('description', '').lower()
            category = ticket.get('category', {}).get('name', '').lower() if ticket.get('category') else ''
            
            # Check if ticket contains termination keywords
            is_termination = any(keyword in title or keyword in description or keyword in category 
                               for keyword in termination_keywords)
            
            if is_termination:
                logger.info(f"Found termination ticket: #{ticket_number} - {ticket.get('name', 'No title')}")
                
                # Extract user information from ticket
                user_info = extract_user_info_from_ticket(ticket)
                
                if user_info:
                    termination_request = {
                        'ticket_id': ticket_id,
                        'ticket_number': ticket_number,
                        'title': ticket.get('name', ''),
                        'description': ticket.get('description', ''),
                        'created_at': ticket.get('created_at', ''),
                        'requester': ticket.get('requester', {}),
                        'state': ticket.get('state', ''),
                        'priority': ticket.get('priority', ''),
                        'category': category,
                        **user_info  # Include extracted user info
                    }
                    termination_requests.append(termination_request)
                    logger.info(f"Added termination request for {user_info.get('name', 'Unknown')} ({user_info.get('email', 'Unknown')})")
                else:
                    logger.warning(f"Could not extract user info from ticket #{ticket_number}")
        
        except Exception as e:
            logger.error(f"Error processing ticket {ticket.get('number', 'Unknown')}: {str(e)}")
            continue
    
    logger.info(f"Found {len(termination_requests)} valid termination requests")
    return termination_requests

def extract_user_info_from_ticket(ticket: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """
    Extract user information (name, email) from a termination ticket.
    
    Args:
        ticket: Ticket dictionary from service desk
        
    Returns:
        Dict with user info if found, None otherwise
    """
    try:
        title = ticket.get('name', '')
        description = ticket.get('description', '')
        
        # Common patterns for extracting user information
        user_info = {}
        
        # Try to extract from custom fields first
        custom_fields = ticket.get('custom_fields_values', [])
        for field in custom_fields:
            field_name = field.get('name', '').lower()
            field_value = field.get('value', '')
            
            if 'email' in field_name and '@' in field_value:
                user_info['email'] = field_value.strip()
            elif 'name' in field_name and field_value:
                user_info['name'] = field_value.strip()
            elif 'employee' in field_name and field_value:
                # Could be employee name or ID
                if '@' in field_value:
                    user_info['email'] = field_value.strip()
                else:
                    user_info['name'] = field_value.strip()
        
        # If custom fields didn't work, try parsing description
        if not user_info.get('email') or not user_info.get('name'):
            parsed_info = parse_user_info_from_text(f"{title}\n{description}")
            user_info.update(parsed_info)
        
        # If we still don't have email, try the requester
        if not user_info.get('email'):
            requester = ticket.get('requester', {})
            requester_email = requester.get('email', '')
            if requester_email and '@' in requester_email:
                user_info['email'] = requester_email
                user_info['name'] = requester.get('name', user_info.get('name', ''))
        
        # Validate we have minimum required info
        if user_info.get('email') and '@' in user_info['email']:
            # Clean up the data
            user_info['email'] = user_info['email'].strip().lower()
            user_info['name'] = user_info.get('name', '').strip()
            
            # If name is still empty, try to derive from email
            if not user_info['name']:
                email_parts = user_info['email'].split('@')[0]
                user_info['name'] = email_parts.replace('.', ' ').replace('_', ' ').title()
            
            return user_info
        else:
            logger.warning(f"Could not extract valid email from ticket #{ticket.get('number', 'Unknown')}")
            return None
            
    except Exception as e:
        logger.error(f"Exception extracting user info: {str(e)}")
        return None

def parse_user_info_from_text(text: str) -> Dict[str, str]:
    """
    Parse user information from ticket text using common patterns.
    
    Args:
        text: Combined title and description text
        
    Returns:
        Dict with parsed user information
    """
    import re
    
    user_info = {}
    
    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_matches = re.findall(email_pattern, text)
    if email_matches:
        user_info['email'] = email_matches[0].lower()
    
    # Name patterns
    name_patterns = [
        r'(?:employee|user|person):\s*([A-Za-z\s]+?)(?:\n|$|\.|\,)',
        r'(?:name|employee name|full name):\s*([A-Za-z\s]+?)(?:\n|$|\.|\,)',
        r'for\s+([A-Za-z]+\s+[A-Za-z]+)',  # "for John Smith"
        r'terminate\s+([A-Za-z]+\s+[A-Za-z]+)',  # "terminate John Smith"
        r'([A-Za-z]+\s+[A-Za-z]+)\s+(?:is leaving|will be leaving|last day)',
    ]
    
    for pattern in name_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Take the first match and clean it up
            name = matches[0].strip()
            # Filter out common non-name words
            if not any(word in name.lower() for word in ['account', 'access', 'system', 'please', 'user']):
                user_info['name'] = name.title()
                break
    
    return user_info

def update_ticket_status(ticket_id: str, status: str, notes: str = "") -> bool:
    """
    Update a ticket's status in the service desk.
    
    Args:
        ticket_id: Service desk ticket ID
        status: New status for the ticket
        notes: Optional notes to add to the ticket
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        base_url = SAMANAGE_BASE_URL
        headers = get_solarwinds_headers()
        
        update_data = {
            'incident': {
                'state': status
            }
        }
        
        # Add notes if provided
        if notes:
            update_data['incident']['description'] = notes
        
        response = requests.put(
            f"{base_url}/incidents/{ticket_id}.json",
            headers=headers,
            json=update_data,
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully updated ticket {ticket_id} to status: {status}")
            return True
        else:
            logger.error(f"Failed to update ticket {ticket_id}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Exception updating ticket {ticket_id}: {str(e)}")
        return False
