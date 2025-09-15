#!/usr/bin/env python3
"""
Test script for SYNQ Prox user deletion using real termination ticket.
Fetches ticket 64570 and extracts the termination email for testing.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from jml_automation.services.synqprox import SynqProxService
from jml_automation.services.solarwinds import SolarWindsService
from jml_automation.parsers.solarwinds_parser import extract_user_email_from_ticket, parse_termination
import logging

# Set up logging to see what happens
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)

def test_synq_delete_from_termination_ticket():
    """Test SYNQ Prox user deletion using email from termination ticket 64570."""
    print("=== Testing SYNQ Prox User Deletion from Termination Ticket 64570 ===")
    
    try:
        # Initialize SolarWinds service to fetch the ticket
        solarwinds_service = SolarWindsService.from_config()
        
        print("Fetching termination ticket 64570...")
        ticket_data = solarwinds_service.fetch_ticket("64570")
        
        if not ticket_data:
            print("ERROR: Failed to fetch ticket 64570")
            return False
        
        print(f"SUCCESS: Successfully fetched ticket 64570: {ticket_data.get('subject', 'No subject')}")
        
        # Extract the termination email
        termination_email = extract_user_email_from_ticket(ticket_data)
        
        if not termination_email:
            print("ERROR: Could not extract termination email from ticket 64570")
            print("Available custom fields:")
            custom_fields = ticket_data.get('custom_fields_values', [])
            for field in custom_fields[:10]:  # Show first 10 fields
                name = field.get('name', 'Unknown')
                value = field.get('value', 'No value')
                print(f"  - {name}: {value}")
            return False
        
        print(f"SUCCESS: Extracted termination email: {termination_email}")
        
        # Initialize SYNQ Prox service
        synq_service = SynqProxService()
        
        print(f"Testing deletion of user: {termination_email}")
        
        # Test the delete function
        result = synq_service.delete_user(termination_email)
        
        if result:
            print(f"SUCCESS: Successfully processed SYNQ Prox deletion for: {termination_email}")
            return True
        else:
            print(f"ERROR: Failed to delete user from SYNQ Prox: {termination_email}")
            return False
            
    except Exception as e:
        print(f"ERROR: Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_synq_delete_from_termination_ticket()
    if success:
        print("\n Test completed successfully!")
    else:
        print("\nFAILED: Test failed!")
        sys.exit(1)
